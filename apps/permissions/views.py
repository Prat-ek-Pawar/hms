from django.shortcuts import render

# Create your views here.
# apps/permissions/views.py
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.db import transaction
from .models import Module, Permission, UserGroup, GroupPermission, UserPermission, PermissionLog
from .serializers import (
    ModuleSerializer, PermissionSerializer, UserGroupSerializer,
    GroupPermissionSerializer, UserPermissionSerializer, PermissionLogSerializer
)
from .mixins import HasPermissionMixin

User = get_user_model()

class ModuleViewSet(viewsets.ModelViewSet):
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer
    permission_classes = [IsAuthenticated, HasPermissionMixin]
    required_permission = 'permissions.read'
    
    def get_queryset(self):
        queryset = Module.objects.all()
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Search functionality
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(display_name__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset.order_by('name')
    
    @action(detail=True, methods=['get'])
    def permissions(self, request, pk=None):
        """Get all permissions for a module"""
        module = self.get_object()
        permissions = module.permissions.filter(is_active=True)
        serializer = PermissionSerializer(permissions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def bulk_create_permissions(self, request):
        """Create permissions for a module automatically"""
        module_id = request.data.get('module_id')
        operations = request.data.get('operations', ['create', 'read', 'update', 'delete'])
        
        if not module_id:
            return Response(
                {'error': 'module_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            module = Module.objects.get(id=module_id)
        except Module.DoesNotExist:
            return Response(
                {'error': 'Module not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        created_permissions = []
        for operation in operations:
            permission, created = Permission.objects.get_or_create(
                module=module,
                operation=operation,
                defaults={'is_active': True}
            )
            if created:
                created_permissions.append(permission)
        
        serializer = PermissionSerializer(created_permissions, many=True)
        return Response({
            'message': f'Created {len(created_permissions)} permissions',
            'permissions': serializer.data
        })

class PermissionViewSet(viewsets.ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated, HasPermissionMixin]
    required_permission = 'permissions.read'
    
    def get_queryset(self):
        queryset = Permission.objects.select_related('module').all()
        
        # Filter by module
        module_id = self.request.query_params.get('module_id')
        if module_id:
            queryset = queryset.filter(module_id=module_id)
        
        # Filter by operation
        operation = self.request.query_params.get('operation')
        if operation:
            queryset = queryset.filter(operation=operation)
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset.order_by('module__name', 'operation')

class UserGroupViewSet(viewsets.ModelViewSet):
    queryset = UserGroup.objects.all()
    serializer_class = UserGroupSerializer
    permission_classes = [IsAuthenticated, HasPermissionMixin]
    required_permission = 'permissions.read'
    
    def get_queryset(self):
        queryset = UserGroup.objects.select_related('group').all()
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Search functionality
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(group__name__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset.order_by('group__name')
    
    @action(detail=True, methods=['post'])
    def add_permission(self, request, pk=None):
        """Add permission to group"""
        user_group = self.get_object()
        permission_id = request.data.get('permission_id')
        
        if not permission_id:
            return Response(
                {'error': 'permission_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            permission = Permission.objects.get(id=permission_id)
        except Permission.DoesNotExist:
            return Response(
                {'error': 'Permission not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        group_permission, created = GroupPermission.objects.get_or_create(
            group=user_group.group,
            permission=permission,
            defaults={'granted_by': request.user}
        )
        
        if created:
            # Log the action
            PermissionLog.objects.create(
                action='grant_group',
                user=request.user,
                permission=permission,
                group=user_group.group,
                details={'group_name': user_group.group.name, 'permission_name': permission.name}
            )
            return Response({'message': 'Permission added to group'})
        else:
            return Response(
                {'message': 'Permission already exists for this group'}, 
                status=status.HTTP_200_OK
            )
    
    @action(detail=True, methods=['post'])
    def remove_permission(self, request, pk=None):
        """Remove permission from group"""
        user_group = self.get_object()
        permission_id = request.data.get('permission_id')
        
        if not permission_id:
            return Response(
                {'error': 'permission_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            group_permission = GroupPermission.objects.get(
                group=user_group.group,
                permission_id=permission_id
            )
            
            # Log the action
            PermissionLog.objects.create(
                action='revoke_group',
                user=request.user,
                permission=group_permission.permission,
                group=user_group.group,
                details={
                    'group_name': user_group.group.name, 
                    'permission_name': group_permission.permission.name
                }
            )
            
            group_permission.delete()
            return Response({'message': 'Permission removed from group'})
        except GroupPermission.DoesNotExist:
            return Response(
                {'error': 'Permission not found for this group'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def add_user(self, request, pk=None):
        """Add user to group"""
        user_group = self.get_object()
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
            user.groups.add(user_group.group)
            
            # Log the action
            PermissionLog.objects.create(
                action='add_user_to_group',
                user=request.user,
                target_user=user,
                group=user_group.group,
                details={'group_name': user_group.group.name, 'user_name': user.full_name}
            )
            
            return Response({'message': f'User {user.full_name} added to group {user_group.group.name}'})
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def remove_user(self, request, pk=None):
        """Remove user from group"""
        user_group = self.get_object()
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
            user.groups.remove(user_group.group)
            
            # Log the action
            PermissionLog.objects.create(
                action='remove_user_from_group',
                user=request.user,
                target_user=user,
                group=user_group.group,
                details={'group_name': user_group.group.name, 'user_name': user.full_name}
            )
            
            return Response({'message': f'User {user.full_name} removed from group {user_group.group.name}'})
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

class UserPermissionViewSet(viewsets.ModelViewSet):
    queryset = UserPermission.objects.all()
    serializer_class = UserPermissionSerializer
    permission_classes = [IsAuthenticated, HasPermissionMixin]
    required_permission = 'permissions.read'
    
    def get_queryset(self):
        queryset = UserPermission.objects.select_related('user', 'permission').all()
        
        # Filter by user
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Filter by permission
        permission_id = self.request.query_params.get('permission_id')
        if permission_id:
            queryset = queryset.filter(permission_id=permission_id)
        
        # Filter by granted status
        is_granted = self.request.query_params.get('is_granted')
        if is_granted is not None:
            queryset = queryset.filter(is_granted=is_granted.lower() == 'true')
        
        return queryset.order_by('-granted_at')
    
    def perform_create(self, serializer):
        serializer.save(granted_by=self.request.user)
        
        # Log the action
        instance = serializer.instance
        PermissionLog.objects.create(
            action='grant_user' if instance.is_granted else 'revoke_user',
            user=self.request.user,
            target_user=instance.user,
            permission=instance.permission,
            details={
                'user_name': instance.user.full_name,
                'permission_name': instance.permission.name,
                'is_granted': instance.is_granted
            }
        )

class PermissionLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PermissionLog.objects.all()
    serializer_class = PermissionLogSerializer
    permission_classes = [IsAuthenticated, HasPermissionMixin]
    required_permission = 'permissions.read'
    
    def get_queryset(self):
        queryset = PermissionLog.objects.select_related(
            'user', 'target_user', 'permission', 'group'
        ).all()
        
        # Filter by action
        action = self.request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action)
        
        # Filter by user who performed the action
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Filter by target user
        target_user_id = self.request.query_params.get('target_user_id')
        if target_user_id:
            queryset = queryset.filter(target_user_id=target_user_id)
        
        return queryset.order_by('-timestamp')

