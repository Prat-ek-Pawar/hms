# apps/permissions/decorators.py (Updated)
from functools import wraps
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import UserPermission

def require_permission(permission_codename):
    """
    Decorator to check if user has specific permission
    Usage: @require_permission('patient.create') or @require_permission('appointments.patient.create')
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if not UserPermission.has_permission(request.user, permission_codename):
                if request.content_type == 'application/json' or request.path.startswith('/api/'):
                    return JsonResponse(
                        {'error': f'Permission denied. Required: {permission_codename}'}, 
                        status=403
                    )
                else:
                    return JsonResponse({'error': 'Permission denied'}, status=403)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def require_model_permission(model_class, operation):
    """
    Decorator that automatically creates permission codename from model
    Usage: @require_model_permission(Patient, 'create')
    """
    def decorator(view_func):
        permission_codename = f"{model_class._meta.model_name}.{operation}"
        return require_permission(permission_codename)(view_func)
    return decorator