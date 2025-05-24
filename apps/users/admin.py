# apps/users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'full_name', 'role', 'department', 'is_active', 'is_staff', 'date_joined']
    list_filter = ['role', 'department', 'is_active', 'is_staff', 'date_joined']
    search_fields = ['email', 'first_name', 'last_name', 'employee_id']
    ordering = ['-date_joined']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Hospital Information', {
            'fields': ('role', 'department', 'employee_id', 'phone', 'date_of_birth', 'address', 'profile_picture')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Hospital Information', {
            'fields': ('email', 'role', 'department', 'employee_id', 'phone')
        }),
    )

