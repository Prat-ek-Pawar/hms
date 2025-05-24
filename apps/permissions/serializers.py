# apps/permissions/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from .models import Module, Permission, UserGroup, GroupPermission, UserPermission, PermissionLog

User = get_user_model()

class ModuleSerializer(serializers.ModelSerializer):
    permissions_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Module
        fields = ['id', 'name', 'display_name', 'description', 'is_active', 'permissions_count', 'created_at']
    
    def get_permissions_count(self, obj):
        return obj.permissions.filter(is_active=True).count()

class PermissionSerializer(serializers.ModelSerializer):
    module_name = serializers.CharField(source='module.name', read_only=True)
    module_display_name = serializers.CharField(source='module.display_name', read_only=True)
    
    class Meta:
        model = Permission
        fields = [
            'id', 'module', 'module_name', 'module_display_name', 'operation',
            'codename', 'name', 'description', 'is_active', 'created_at'
        ]
        read_only_fields = ['codename', 'name']

class UserGroupSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='group.name')
    users_count = serializers.ReadOnlyField()
    permissions = serializers.SerializerMethodField()
    users = serializers.SerializerMethodField()
    
    class Meta:
        model = UserGroup
        fields = [
            'id', 'name', 'description', 'is_active', 'users_count',
            'permissions', 'users', 'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']
    
    def get_permissions(self, obj):
        group_permissions = GroupPermission.objects.filter(group=obj.group).select_related('permission')
        return [
            {
                'id': gp.permission.id,
                'codename': gp.permission.codename,
                'name': gp.permission.name,
                'module': gp.permission.module.display_name,
                'operation': gp.permission.get_operation_display()
            }
            for gp in group_permissions
        ]
    
    def get_users(self, obj):
        users = obj.group.user_set.all()
        return [
            {
                'id': user.id,
                'full_name': user.full_name,
                'email': user.email,
                'role': user.role
            }
            for user in users
        ]
    
    def create(self, validated_data):
        group_data = validated_data.pop('group')
        group = Group.objects.create(name=group_data['name'])
        user_group = UserGroup.objects.create(
            group=group,
            created_by=self.context['request'].user,
            **validated_data
        )
        return user_group
    
    def update(self, instance, validated_data):
        group_data = validated_data.pop('group', None)
        if group_data and 'name' in group_data:
            instance.group.name = group_data['name']
            instance.group.save()
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class GroupPermissionSerializer(serializers.ModelSerializer):
    permission_name = serializers.CharField(source='permission.name', read_only=True)
    permission_codename = serializers.CharField(source='permission.codename', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    
    class Meta:
        model = GroupPermission
        fields = [
            'id', 'group', 'group_name', 'permission', 'permission_name',
            'permission_codename', 'granted_by', 'granted_at'
        ]
        read_only_fields = ['granted_by', 'granted_at']

class UserPermissionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    permission_name = serializers.CharField(source='permission.name', read_only=True)
    permission_codename = serializers.CharField(source='permission.codename', read_only=True)
    
    class Meta:
        model = UserPermission
        fields = [
            'id', 'user', 'user_name', 'user_email', 'permission',
            'permission_name', 'permission_codename', 'is_granted',
            'granted_by', 'granted_at'
        ]
        read_only_fields = ['granted_by', 'granted_at']

class PermissionLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    target_user_name = serializers.CharField(source='target_user.full_name', read_only=True)
    permission_name = serializers.CharField(source='permission.name', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    
    class Meta:
        model = PermissionLog
        fields = [
            'id', 'action', 'user', 'user_name', 'target_user', 'target_user_name',
            'permission', 'permission_name', 'group', 'group_name',
            'details', 'timestamp'
        ]