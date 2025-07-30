# apps/permissions/models.py (Updated to use ContentType)

from django.db import models
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.apps import apps

class Permission(models.Model):
    """
    Custom permission model using ContentType for dynamic module discovery
    """
    OPERATION_CHOICES = [
        ('create', 'Create'),
        ('read', 'Read'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('export', 'Export'),
        ('import', 'Import'),
        ('approve', 'Approve'),
        ('reject', 'Reject'),
    ]
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='custom_permissions')
    operation = models.CharField(max_length=20, choices=OPERATION_CHOICES)
    codename = models.CharField(max_length=100, unique=True)  # e.g., 'appointment.create', 'patient.read'
    name = models.CharField(max_length=200)  # e.g., 'Can create appointments'
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'custom_permissions'
        unique_together = ['content_type', 'operation']
        ordering = ['content_type__app_label', 'content_type__model', 'operation']
    
    def __str__(self):
        return f"{self.content_type.model_class()._meta.verbose_name} - {self.get_operation_display()}"
    
    @property
    def module_name(self):
        """Get module name from content type"""
        return self.content_type.model
    
    @property
    def app_label(self):
        """Get app label from content type"""
        return self.content_type.app_label
    
    def save(self, *args, **kwargs):
        if not self.codename:
            self.codename = f"{self.content_type.model}.{self.operation}"
        if not self.name:
            model_name = self.content_type.model_class()._meta.verbose_name
            self.name = f"Can {self.operation} {model_name}"
        super().save(*args, **kwargs)
    
    @classmethod
    def create_permissions_for_model(cls, model_class, operations=None):
        """
        Create permissions for a model automatically
        Usage: Permission.create_permissions_for_model(Patient, ['create', 'read', 'update', 'delete'])
        """
        if operations is None:
            operations = ['create', 'read', 'update', 'delete']
        
        content_type = ContentType.objects.get_for_model(model_class)
        created_permissions = []
        
        for operation in operations:
            permission, created = cls.objects.get_or_create(
                content_type=content_type,
                operation=operation,
                defaults={'is_active': True}
            )
            if created:
                created_permissions.append(permission)
        
        return created_permissions
    
    @classmethod
    def get_permissions_for_app(cls, app_label):
        """Get all permissions for an app"""
        content_types = ContentType.objects.filter(app_label=app_label)
        return cls.objects.filter(content_type__in=content_types, is_active=True)

class UserPermission(models.Model):
    """
    Direct user permissions (overrides group permissions)
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='custom_user_permissions'
    )
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    is_granted = models.BooleanField(default=True)  # False means explicitly denied
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='granted_user_permissions'
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_permissions'
        unique_together = ['user', 'permission']
    
    def __str__(self):
        status = "Granted" if self.is_granted else "Denied"
        return f"{self.user.get_full_name()} - {self.permission.name} ({status})"
    
    @classmethod
    def has_permission(cls, user, permission_codename):
        """
        Check if user has a specific permission
        Format: 'model_name.operation' or 'app_label.model_name.operation'
        """
        if not user.is_authenticated:
            return False
        
        # Handle both formats: 'patient.create' and 'appointments.patient.create'
        parts = permission_codename.split('.')
        if len(parts) == 2:
            model_name, operation = parts
            # Try to find the permission by model name only
            try:
                permission = Permission.objects.get(
                    content_type__model=model_name,
                    operation=operation,
                    is_active=True
                )
            except Permission.DoesNotExist:
                return False
        elif len(parts) == 3:
            app_label, model_name, operation = parts
            try:
                content_type = ContentType.objects.get(app_label=app_label, model=model_name)
                permission = Permission.objects.get(
                    content_type=content_type,
                    operation=operation,
                    is_active=True
                )
            except (ContentType.DoesNotExist, Permission.DoesNotExist):
                return False
        else:
            return False
        
        # Check for explicit denial
        if cls.objects.filter(user=user, permission=permission, is_granted=False).exists():
            return False
        
        # Check direct permission
        if cls.objects.filter(user=user, permission=permission, is_granted=True).exists():
            return True
        
        # Check group permissions
        user_groups = user.groups.all()
        return GroupPermission.objects.filter(
            group__in=user_groups,
            permission=permission
        ).exists()
    
    @classmethod
    def get_user_permissions(cls, user):
        """Get all effective permissions for a user"""
        if not user.is_authenticated:
            return []
        
        # Get direct user permissions
        direct_permissions = cls.objects.filter(user=user, is_granted=True).select_related('permission')
        direct_denied = cls.objects.filter(user=user, is_granted=False).values_list('permission_id', flat=True)
        
        # Get group permissions
        user_groups = user.groups.all()
        group_permissions = GroupPermission.objects.filter(
            group__in=user_groups
        ).select_related('permission').exclude(permission_id__in=direct_denied)
        
        # Combine permissions
        permissions = set()
        
        # Add direct permissions
        for perm in direct_permissions:
            permissions.add(perm.permission.codename)
        
        # Add group permissions (if not explicitly denied)
        for group_perm in group_permissions:
            permissions.add(group_perm.permission.codename)
        
        return list(permissions)

class GroupPermission(models.Model):
    """Maps permissions to groups"""
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='group_permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    granted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    granted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'group_permissions'
        unique_together = ['group', 'permission']
    
    def __str__(self):
        return f"{self.group.name} - {self.permission.name}"

# Management command or utility function to auto-create permissions
class PermissionManager:
    """Utility class to manage permissions automatically"""
    
    @staticmethod
    def create_permissions_for_app(app_label, operations=None):
        """Create permissions for all models in an app"""
        if operations is None:
            operations = ['create', 'read', 'update', 'delete']
        
        app_config = apps.get_app_config(app_label)
        created_permissions = []
        
        for model in app_config.get_models():
            permissions = Permission.create_permissions_for_model(model, operations)
            created_permissions.extend(permissions)
        
        return created_permissions
    
    @staticmethod
    def create_all_permissions():
        """Create permissions for all installed apps (excluding system apps)"""
        system_apps = [
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
        ]
        
        all_permissions = []
        for app_config in apps.get_app_configs():
            if app_config.name not in system_apps:
                permissions = PermissionManager.create_permissions_for_app(
                    app_config.label
                )
                all_permissions.extend(permissions)
        
        return all_permissions