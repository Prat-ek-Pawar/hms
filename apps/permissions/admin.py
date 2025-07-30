# apps/permissions/admin.py

from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.utils.html import format_html
from django.urls import reverse
from django.apps import apps
from .models import Permission, UserPermission, GroupPermission, PermissionManager

@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['name', 'content_type', 'operation', 'codename', 'is_active', 'created_at']
    list_filter = ['content_type', 'operation', 'is_active', 'created_at']
    search_fields = ['name', 'codename', 'description']
    readonly_fields = ['codename', 'created_at']
    
    fieldsets = (
        (None, {
            'fields': ('content_type', 'operation', 'name', 'description', 'is_active')
        }),
        ('System Info', {
            'fields': ('codename', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('content_type')
    
    actions = ['activate_permissions', 'deactivate_permissions']
    
    def activate_permissions(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} permissions activated.")
    activate_permissions.short_description = "Activate selected permissions"
    
    def deactivate_permissions(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} permissions deactivated.")
    deactivate_permissions.short_description = "Deactivate selected permissions"

@admin.register(UserPermission)
class UserPermissionAdmin(admin.ModelAdmin):
    list_display = ['user', 'permission', 'is_granted', 'granted_by', 'granted_at']
    list_filter = ['is_granted', 'permission__content_type', 'permission__operation', 'granted_at']
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'permission__name']
    raw_id_fields = ['user', 'granted_by']
    readonly_fields = ['granted_at']
    
    fieldsets = (
        (None, {
            'fields': ('user', 'permission', 'is_granted')
        }),
        ('Audit Info', {
            'fields': ('granted_by', 'granted_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'permission', 'granted_by')
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set granted_by for new objects
            obj.granted_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(GroupPermission)
class GroupPermissionAdmin(admin.ModelAdmin):
    list_display = ['group', 'permission', 'granted_by', 'granted_at']
    list_filter = ['permission__content_type', 'permission__operation', 'granted_at']
    search_fields = ['group__name', 'permission__name']
    raw_id_fields = ['granted_by']
    readonly_fields = ['granted_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('group', 'permission', 'granted_by')
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.granted_by = request.user
        super().save_model(request, obj, form, change)

# Custom admin for better Group management
class GroupPermissionInline(admin.TabularInline):
    model = GroupPermission
    extra = 0
    raw_id_fields = ['permission']
    readonly_fields = ['granted_by', 'granted_at']

class CustomGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'permissions_count', 'users_count']
    search_fields = ['name']
    inlines = [GroupPermissionInline]
    
    def permissions_count(self, obj):
        return obj.group_permissions.count()
    permissions_count.short_description = "Permissions"
    
    def users_count(self, obj):
        return obj.user_set.count()
    users_count.short_description = "Users"
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('group_permissions', 'user_set')

# Unregister the default Group admin and register our custom one
admin.site.unregister(Group)
admin.site.register(Group, CustomGroupAdmin)

# Custom admin action to create permissions
class PermissionManagerAdmin(admin.ModelAdmin):
    """
    Admin interface for managing permissions in bulk
    """
    change_list_template = "admin/permissions/permission_manager.html"
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return True
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        # Get all apps and their models
        app_models = {}
        system_apps = [
            'django.contrib.admin',
            'django.contrib.auth', 
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
        ]
        
        for app_config in apps.get_app_configs():
            if app_config.name not in system_apps:
                models = []
                for model in app_config.get_models():
                    content_type = ContentType.objects.get_for_model(model)
                    existing_permissions = Permission.objects.filter(
                        content_type=content_type
                    ).count()
                    
                    models.append({
                        'name': model._meta.verbose_name,
                        'model_name': model._meta.model_name,
                        'existing_permissions': existing_permissions,
                        'content_type_id': content_type.id,
                    })
                
                if models:
                    app_models[app_config.verbose_name] = {
                        'label': app_config.label,
                        'models': models
                    }
        
        extra_context['app_models'] = app_models
        extra_context['operations'] = Permission.OPERATION_CHOICES
        
        # Handle permission creation
        if request.method == 'POST':
            app_label = request.POST.get('app_label')
            model_name = request.POST.get('model_name')
            operations = request.POST.getlist('operations')
            
            if app_label and operations:
                if model_name:
                    # Create permissions for specific model
                    try:
                        model_class = apps.get_model(app_label, model_name)
                        created = Permission.create_permissions_for_model(model_class, operations)
                        self.message_user(request, f"Created {len(created)} permissions for {model_class._meta.verbose_name}")
                    except LookupError:
                        self.message_user(request, f"Model {model_name} not found in {app_label}", level='ERROR')
                else:
                    # Create permissions for entire app
                    created = PermissionManager.create_permissions_for_app(app_label, operations)
                    self.message_user(request, f"Created {len(created)} permissions for {app_label}")
        
        return super().changelist_view(request, extra_context)

# Register the permission manager
admin.site.register(Permission, PermissionManagerAdmin)