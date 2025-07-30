# apps/permissions/mixins.py (Updated)
from rest_framework.permissions import BasePermission
from django.contrib.contenttypes.models import ContentType
from .models import UserPermission

class ModelPermissionMixin(BasePermission):
    """
    Automatic permission checking based on model and HTTP method
    Usage in view: permission_classes = [ModelPermissionMixin]
                  model = Patient  # The model class
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Get model from view
        model_class = getattr(view, 'model', None)
        if hasattr(view, 'get_queryset'):
            try:
                model_class = view.get_queryset().model
            except:
                pass
        
        if not model_class:
            return True  # No model specified, allow access
        
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
        
        permission_codename = f"{model_class._meta.model_name}.{operation}"
        return UserPermission.has_permission(request.user, permission_codename)

class DRFModelPermissionMixin:
    """
    Mixin for DRF ViewSets with automatic model-based permission checking
    Usage: class PatientViewSet(DRFModelPermissionMixin, ModelViewSet):
               # No additional setup needed!
    """
    
    def get_required_permission(self, action=None):
        """Get required permission based on action and model"""
        model_class = getattr(self, 'model', None)
        if hasattr(self, 'get_queryset'):
            try:
                model_class = self.get_queryset().model
            except:
                pass
        
        if not model_class:
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
        return f"{model_class._meta.model_name}.{operation}"
    
    def check_permissions(self, request):
        """Override to check custom permissions"""
        super().check_permissions(request)
        
        required_permission = self.get_required_permission()
        if required_permission and not UserPermission.has_permission(request.user, required_permission):
            self.permission_denied(
                request,
                message=f'Permission denied. Required: {required_permission}'
            )