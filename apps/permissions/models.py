# apps/permissions/models.py (UPDATED - Fix the related_name clash)

from django.db import models
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class Module(models.Model):
    """
    Represents different modules in the hospital management system
    """
    name = models.CharField(max_length=100, unique=True)  # e.g., 'patients', 'appointments', 'inventory'
    display_name = models.CharField(max_length=100)  # e.g., 'Patient Management', 'Appointments'
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'modules'
        ordering = ['name']
    
    def __str__(self):
        return self.display_name

class Permission(models.Model):
    """
    Custom permission model for fine-grained access control
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
    
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='permissions')
    operation = models.CharField(max_length=20, choices=OPERATION_CHOICES)
    codename = models.CharField(max_length=100, unique=True)  # e.g., 'patients.create', 'appointments.read'
    name = models.CharField(max_length=200)  # e.g., 'Can create patients', 'Can view appointments'
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'permissions'
        unique_together = ['module', 'operation']
        ordering = ['module__name', 'operation']
    
    def __str__(self):
        return f"{self.module.display_name} - {self.get_operation_display()}"
    
    def save(self, *args, **kwargs):
        if not self.codename:
            self.codename = f"{self.module.name}.{self.operation}"
        if not self.name:
            self.name = f"Can {self.operation} {self.module.display_name.lower()}"
        super().save(*args, **kwargs)

class UserGroup(models.Model):
    """
    Extended Group model with additional metadata
    """
    group = models.OneToOneField(Group, on_delete=models.CASCADE, related_name='user_group')
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_groups'
        ordering = ['group__name']
    
    def __str__(self):
        return self.group.name
    
    @property
    def name(self):
        return self.group.name
    
    @property
    def users_count(self):
        return self.group.user_set.count()

class GroupPermission(models.Model):
    """
    Maps permissions to groups
    """
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='group_permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    granted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    granted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'group_permissions'
        unique_together = ['group', 'permission']
    
    def __str__(self):
        return f"{self.group.name} - {self.permission.name}"

class UserPermission(models.Model):
    """
    Direct user permissions (overrides group permissions)
    """
    # FIXED: Changed related_name to avoid clash with Django's built-in user_permissions
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='custom_user_permissions'  # CHANGED FROM 'user_permissions'
    )
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    is_granted = models.BooleanField(default=True)  # False means explicitly denied
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='granted_user_permissions'  # ADDED RELATED_NAME
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_permissions'
        unique_together = ['user', 'permission']
    
    def __str__(self):
        status = "Granted" if self.is_granted else "Denied"
        return f"{self.user.get_full_name()} - {self.permission.name} ({status})"
    
    @classmethod
    def get_user_permissions(cls, user):
        """
        Get all effective permissions for a user (combines group and direct permissions)
        """
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
    
    @classmethod
    def has_permission(cls, user, permission_codename):
        """
        Check if user has a specific permission
        """
        # Check for explicit denial
        if cls.objects.filter(user=user, permission__codename=permission_codename, is_granted=False).exists():
            return False
        
        # Check direct permission
        if cls.objects.filter(user=user, permission__codename=permission_codename, is_granted=True).exists():
            return True
        
        # Check group permissions
        user_groups = user.groups.all()
        return GroupPermission.objects.filter(
            group__in=user_groups,
            permission__codename=permission_codename
        ).exists()

class PermissionLog(models.Model):
    """
    Audit log for permission changes
    """
    ACTION_CHOICES = [
        ('grant_user', 'Grant User Permission'),
        ('revoke_user', 'Revoke User Permission'),
        ('grant_group', 'Grant Group Permission'),
        ('revoke_group', 'Revoke Group Permission'),
        ('add_user_to_group', 'Add User to Group'),
        ('remove_user_from_group', 'Remove User from Group'),
    ]
    
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='permission_logs')
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='target_permission_logs'
    )
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, null=True, blank=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'permission_logs'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.get_action_display()} by {self.user.get_full_name()} at {self.timestamp}"