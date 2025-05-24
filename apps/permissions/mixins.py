# apps/permissions/mixins.py
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework import status
from .models import UserPermission

class HasPermissionMixin(BasePermission):
    """
    Custom permission class for DRF views
    Usage in view: permission_classes = [HasPermissionMixin]
           required_permission = 'patients.create'
    """
    required_permission = None
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Get required permission from view
        permission_codename = getattr(view, 'required_permission', self.required_permission)
        
        if not permission_codename:
            return True  # No specific permission required
        
        return UserPermission.has_permission(request.user, permission_codename)

class ModuleCRUDPermissionMixin(BasePermission):
    """
    Automatic CRUD permission checking based on HTTP method and module
    Usage in view: permission_classes = [ModuleCRUDPermissionMixin]
           module_name = 'patients'
    """
    module_name = None
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        module_name = getattr(view, 'module_name', self.module_name)
        if not module_name:
            return True
        
        # Map HTTP methods to operations
        method_operation_map = {
            'GET': 'read',
            'POST': 'create',
            'PUT': 'update',
            'PATCH': 'update',
            'DELETE': 'delete',
        }
        
        operation = method_operation_map.get(request.method)
        if not operation:
            return False
        
        permission_codename = f"{module_name}.{operation}"
        return UserPermission.has_permission(request.user, permission_codename)

class PermissionRequiredMixin:
    """
    Mixin for Django views to check permissions
    Usage: class MyView(PermissionRequiredMixin, View):
               required_permission = 'patients.create'
    """
    required_permission = None
    required_permissions = None  # List of permissions (all required)
    required_any_permissions = None  # List of permissions (any required)
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        # Check single permission
        if self.required_permission:
            if not UserPermission.has_permission(request.user, self.required_permission):
                return JsonResponse(
                    {'error': f'Permission denied. Required: {self.required_permission}'}, 
                    status=403
                )
        
        # Check multiple permissions (all required)
        if self.required_permissions:
            for perm in self.required_permissions:
                if not UserPermission.has_permission(request.user, perm):
                    return JsonResponse(
                        {'error': f'Permission denied. Required: {perm}'}, 
                        status=403
                    )
        
        # Check multiple permissions (any required)
        if self.required_any_permissions:
            has_any = any(
                UserPermission.has_permission(request.user, perm) 
                for perm in self.required_any_permissions
            )
            if not has_any:
                return JsonResponse(
                    {'error': f'Permission denied. Required one of: {", ".join(self.required_any_permissions)}'}, 
                    status=403
                )
        
        return super().dispatch(request, *args, **kwargs)

class DRFPermissionMixin:
    """
    Mixin for DRF ViewSets with automatic CRUD permission checking
    Usage: class PatientViewSet(DRFPermissionMixin, ModelViewSet):
               module_name = 'patients'
    """
    module_name = None
    
    def get_required_permission(self, action=None):
        """Get required permission based on action"""
        if not self.module_name:
            return None
        
        current_action = action or self.action
        
        action_permission_map = {
            'list': 'read',
            'retrieve': 'read',
            'create': 'create',
            'update': 'update',
            'partial_update': 'update',
            'destroy': 'delete',
        }
        
        operation = action_permission_map.get(current_action, 'read')
        return f"{self.module_name}.{operation}"
    
    def check_permissions(self, request):
        """Override to check custom permissions"""
        super().check_permissions(request)
        
        required_permission = self.get_required_permission()
        if required_permission and not UserPermission.has_permission(request.user, required_permission):
            self.permission_denied(
                request, 
                message=f'Permission denied. Required: {required_permission}'
            )