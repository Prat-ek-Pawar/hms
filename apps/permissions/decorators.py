# apps/permissions/decorators.py
from functools import wraps
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from rest_framework.response import Response
from rest_framework import status
from .models import UserPermission

def require_permission(permission_codename):
    """
    Decorator to check if user has specific permission
    Usage: @require_permission('patients.create')
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

def require_any_permission(*permission_codenames):
    """
    Decorator to check if user has any of the specified permissions
    Usage: @require_any_permission('patients.read', 'patients.update')
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            has_permission = any(
                UserPermission.has_permission(request.user, perm) 
                for perm in permission_codenames
            )
            if not has_permission:
                if request.content_type == 'application/json' or request.path.startswith('/api/'):
                    return JsonResponse(
                        {'error': f'Permission denied. Required one of: {", ".join(permission_codenames)}'}, 
                        status=403
                    )
                else:
                    return JsonResponse({'error': 'Permission denied'}, status=403)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def require_all_permissions(*permission_codenames):
    """
    Decorator to check if user has all specified permissions
    Usage: @require_all_permissions('patients.read', 'patients.update')
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            has_all_permissions = all(
                UserPermission.has_permission(request.user, perm) 
                for perm in permission_codenames
            )
            if not has_all_permissions:
                if request.content_type == 'application/json' or request.path.startswith('/api/'):
                    return JsonResponse(
                        {'error': f'Permission denied. Required all of: {", ".join(permission_codenames)}'}, 
                        status=403
                    )
                else:
                    return JsonResponse({'error': 'Permission denied'}, status=403)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

