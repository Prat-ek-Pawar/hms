# apps/permissions/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

User = get_user_model()

class Module(models.Model):
    """
    Represents different modules/apps in the system
    """
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'permission_modules'
        ordering = ['name']

    def __str__(self):
        return self.display_name or self.name

class Permission(models.Model):
    """
    Represents specific permissions within modules
    """
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('read', 'Read/View'),
        ('update', 'Update/Edit'),
        ('delete', 'Delete'),
        ('export', 'Export'),
        ('import', 'Import'),
        ('manage', 'Manage/Admin'),
    ]

    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='permissions')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'permissions'
        unique_together = ['module', 'action']
        ordering = ['module__name', 'action']

    def __str__(self):
        return f"{self.module.name}.{self.action}"

    @property
    def permission_code(self):
        return f"{self.module.name}.{self.action}"

class Role(models.Model):
    """
    User roles with predefined permissions
    """
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    permissions = models.ManyToManyField(Permission, related_name='roles')
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'roles'
        ordering = ['name']

    def __str__(self):
        return self.display_name or self.name

    def save(self, *args, **kwargs):
        if self.is_default:
            # Ensure only one default role
            Role.objects.filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)

class UserPermission(models.Model):
    """
    Direct user permissions (overrides role permissions)
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    is_granted = models.BooleanField(default=True)  # True = granted, False = explicitly denied
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='granted_permissions')
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'user_permissions'
        unique_together = ['user', 'permission']

    def __str__(self):
        status = "granted" if self.is_granted else "denied"
        return f"{self.user.username} - {self.permission.permission_code} ({status})"

class UserRole(models.Model):
    """
    User role assignments
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_roles')
    assigned_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'user_roles'
        unique_together = ['user', 'role']

    def __str__(self):
        return f"{self.user.username} - {self.role.name}"

class PermissionManager:
    """
    Centralized permission management
    """
    @staticmethod
    def has_permission(user, permission_code):
        """
        Check if user has a specific permission
        Args:
            user: User instance
            permission_code: string in format 'module.action' (e.g., 'appointments.read')
        """
        if not user or not user.is_authenticated:
            return False

        # Superuser has all permissions
        if user.is_superuser:
            return True

        # Check cache first
        cache_key = f"user_permission_{user.id}_{permission_code}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # Parse permission code
        try:
            module_name, action = permission_code.split('.', 1)
        except ValueError:
            return False

        # Get permission object
        try:
            permission = Permission.objects.get(
                module__name=module_name,
                action=action,
                is_active=True,
                module__is_active=True
            )
        except Permission.DoesNotExist:
            cache.set(cache_key, False, 300)  # Cache for 5 minutes
            return False

        # Check direct user permission first (highest priority)
        user_perm = UserPermission.objects.filter(
            user=user,
            permission=permission
        ).first()

        if user_perm:
            result = user_perm.is_granted
            cache.set(cache_key, result, 300)
            return result

        # Check role-based permissions
        user_roles = UserRole.objects.filter(
            user=user,
            role__is_active=True
        ).select_related('role')

        for user_role in user_roles:
            if permission in user_role.role.permissions.all():
                cache.set(cache_key, True, 300)
                return True

        # No permission found
        cache.set(cache_key, False, 300)
        return False

    @staticmethod
    def get_user_permissions(user):
        """Get all permissions for a user"""
        if not user or not user.is_authenticated:
            return []

        if user.is_superuser:
            return list(Permission.objects.filter(is_active=True).values_list('module__name', 'action'))

        permissions = set()

        # Get role-based permissions
        user_roles = UserRole.objects.filter(
            user=user,
            role__is_active=True
        ).prefetch_related('role__permissions')

        for user_role in user_roles:
            for perm in user_role.role.permissions.filter(is_active=True):
                permissions.add((perm.module.name, perm.action))

        # Get direct user permissions (can override role permissions)
        user_perms = UserPermission.objects.filter(
            user=user,
            permission__is_active=True
        ).select_related('permission__module')

        for user_perm in user_perms:
            perm_tuple = (user_perm.permission.module.name, user_perm.permission.action)
            if user_perm.is_granted:
                permissions.add(perm_tuple)
            else:
                permissions.discard(perm_tuple)  # Remove if explicitly denied

        return [f"{module}.{action}" for module, action in permissions]

    @staticmethod
    def grant_permission(user, permission_code, granted_by=None):
        """Grant a permission to a user"""
        try:
            module_name, action = permission_code.split('.', 1)
            permission = Permission.objects.get(
                module__name=module_name,
                action=action
            )

            user_perm, created = UserPermission.objects.get_or_create(
                user=user,
                permission=permission,
                defaults={'granted_by': granted_by}
            )
            user_perm.is_granted = True
            user_perm.save()

            # Clear cache
            cache_key = f"user_permission_{user.id}_{permission_code}"
            cache.delete(cache_key)

            return True
        except (ValueError, Permission.DoesNotExist):
            return False

    @staticmethod
    def revoke_permission(user, permission_code):
        """Revoke a permission from a user"""
        try:
            module_name, action = permission_code.split('.', 1)
            permission = Permission.objects.get(
                module__name=module_name,
                action=action
            )

            UserPermission.objects.filter(
                user=user,
                permission=permission
            ).delete()

            # Clear cache
            cache_key = f"user_permission_{user.id}_{permission_code}"
            cache.delete(cache_key)

            return True
        except (ValueError, Permission.DoesNotExist):
            return False

    @staticmethod
    def assign_role(user, role_name, assigned_by=None):
        """Assign a role to a user"""
        try:
            role = Role.objects.get(name=role_name, is_active=True)
            user_role, created = UserRole.objects.get_or_create(
                user=user,
                role=role,
                defaults={'assigned_by': assigned_by}
            )

            # Clear all permission cache for this user
            PermissionManager._clear_user_cache(user)

            return True
        except Role.DoesNotExist:
            return False

    @staticmethod
    def _clear_user_cache(user):
        """Clear all cached permissions for a user"""
        # This is a simplified version - in production you might want to use cache tags
        pass

# Signal handlers to clear cache when permissions change
@receiver([post_save, post_delete], sender=UserPermission)
@receiver([post_save, post_delete], sender=UserRole)
def clear_permission_cache(sender, instance, **kwargs):
    if hasattr(instance, 'user'):
        user_id = instance.user.id
        # Clear user-specific cache patterns
        # In production, you might want to implement a more sophisticated cache invalidation
        pass
