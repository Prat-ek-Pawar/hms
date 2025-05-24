# apps/permissions/admin.py
from django.contrib import admin
from django.contrib.auth.models import Group
from .models import Module, Permission, UserGroup, GroupPermission, UserPermission, PermissionLog

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'display_name', 'description']
    ordering = ['name']

@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['name', 'module', 'operation', 'codename', 'is_active', 'created_at']
    list_filter = ['module', 'operation', 'is_active', 'created_at']
    search_fields = ['name', 'codename', 'description']
    ordering = ['module__name', 'operation']

@admin.register(UserGroup)
class UserGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'users_count', 'is_active', 'created_by', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['group__name', 'description']
    ordering = ['group__name']

@admin.register(GroupPermission)
class GroupPermissionAdmin(admin.ModelAdmin):
    list_display = ['group', 'permission', 'granted_by', 'granted_at']
    list_filter = ['granted_at']
    search_fields = ['group__name', 'permission__name', 'permission__codename']
    ordering = ['-granted_at']

@admin.register(UserPermission)
class UserPermissionAdmin(admin.ModelAdmin):
    list_display = ['user', 'permission', 'is_granted', 'granted_by', 'granted_at']
    list_filter = ['is_granted', 'granted_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'permission__name']
    ordering = ['-granted_at']

@admin.register(PermissionLog)
class PermissionLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'user', 'target_user', 'permission', 'group', 'timestamp']
    list_filter = ['action', 'timestamp']
    search_fields = ['user__email', 'target_user__email', 'permission__name', 'group__name']
    ordering = ['-timestamp']
    readonly_fields = ['timestamp']

# apps/users/management/commands/create_hospital_data.py
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from apps.permissions.models import Module, Permission, UserGroup, GroupPermission

User = get_user_model()

class Command(BaseCommand):
    help = 'Create initial hospital management data including modules, permissions, and groups'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating hospital management initial data...'))
        
        # Create modules
        modules_data = [
            {'name': 'patients', 'display_name': 'Patient Management', 'description': 'Manage patient records and information'},
            {'name': 'appointments', 'display_name': 'Appointments', 'description': 'Schedule and manage appointments'},
            {'name': 'medical_records', 'display_name': 'Medical Records', 'description': 'Patient medical history and records'},
            {'name': 'pharmacy', 'display_name': 'Pharmacy', 'description': 'Medicine inventory and prescriptions'},
            {'name': 'laboratory', 'display_name': 'Laboratory', 'description': 'Lab tests and results'},
            {'name': 'billing', 'display_name': 'Billing', 'description': 'Patient billing and payments'},
            {'name': 'inventory', 'display_name': 'Inventory', 'description': 'Medical equipment and supplies'},
            {'name': 'reports', 'display_name': 'Reports', 'description': 'System reports and analytics'},
            {'name': 'users', 'display_name': 'User Management', 'description': 'Manage system users'},
            {'name': 'permissions', 'display_name': 'Permission Management', 'description': 'Manage user permissions and roles'},
        ]
        
        for module_data in modules_data:
            module, created = Module.objects.get_or_create(
                name=module_data['name'],
                defaults=module_data
            )
            if created:
                self.stdout.write(f'Created module: {module.display_name}')
            
            # Create permissions for each module
            operations = ['create', 'read', 'update', 'delete']
            if module_data['name'] in ['reports', 'medical_records']:
                operations.append('export')
            if module_data['name'] in ['billing', 'pharmacy']:
                operations.extend(['approve', 'reject'])
            
            for operation in operations:
                permission, created = Permission.objects.get_or_create(
                    module=module,
                    operation=operation
                )
                if created:
                    self.stdout.write(f'Created permission: {permission.name}')
        
        # Create user groups with permissions
        groups_data = [
            {
                'name': 'Administrators',
                'description': 'Full system access',
                'permissions': ['*']  # All permissions
            },
            {
                'name': 'Doctors',
                'description': 'Medical staff with patient care access',
                'permissions': [
                    'patients.read', 'patients.update', 'patients.create',
                    'medical_records.read', 'medical_records.create', 'medical_records.update',
                    'appointments.read', 'appointments.create', 'appointments.update',
                    'laboratory.read', 'laboratory.create',
                    'pharmacy.read', 'pharmacy.create',
                    'reports.read', 'reports.export'
                ]
            },
            {
                'name': 'Nurses',
                'description': 'Nursing staff with patient care support',
                'permissions': [
                    'patients.read', 'patients.update',
                    'medical_records.read', 'medical_records.create',
                    'appointments.read', 'appointments.update',
                    'laboratory.read',
                    'pharmacy.read'
                ]
            },
            {
                'name': 'Receptionists',
                'description': 'Front desk staff for appointments and basic patient info',
                'permissions': [
                    'patients.read', 'patients.create', 'patients.update',
                    'appointments.read', 'appointments.create', 'appointments.update', 'appointments.delete',
                    'billing.read', 'billing.create'
                ]
            },
            {
                'name': 'Pharmacists',
                'description': 'Pharmacy staff for medicine management',
                'permissions': [
                    'patients.read',
                    'pharmacy.read', 'pharmacy.create', 'pharmacy.update', 'pharmacy.approve',
                    'inventory.read', 'inventory.update',
                    'reports.read'
                ]
            },
            {
                'name': 'Lab Technicians',
                'description': 'Laboratory staff for test management',
                'permissions': [
                    'patients.read',
                    'laboratory.read', 'laboratory.create', 'laboratory.update',
                    'reports.read'
                ]
            },
            {
                'name': 'Billing Staff',
                'description': 'Financial staff for billing operations',
                'permissions': [
                    'patients.read',
                    'billing.read', 'billing.create', 'billing.update',
                    'reports.read', 'reports.export'
                ]
            }
        ]
        
        for group_data in groups_data:
            # Create Django Group
            django_group, created = Group.objects.get_or_create(name=group_data['name'])
            if created:
                self.stdout.write(f'Created Django group: {django_group.name}')
            
            # Create UserGroup
            user_group, created = UserGroup.objects.get_or_create(
                group=django_group,
                defaults={'description': group_data['description']}
            )
            if created:
                self.stdout.write(f'Created user group: {user_group.name}')
            
            # Assign permissions
            if '*' in group_data['permissions']:
                # Give all permissions to administrators
                all_permissions = Permission.objects.filter(is_active=True)
                for permission in all_permissions:
                    GroupPermission.objects.get_or_create(
                        group=django_group,
                        permission=permission
                    )
                self.stdout.write(f'Assigned all permissions to {user_group.name}')
            else:
                for permission_codename in group_data['permissions']:
                    try:
                        permission = Permission.objects.get(codename=permission_codename)
                        GroupPermission.objects.get_or_create(
                            group=django_group,
                            permission=permission
                        )
                    except Permission.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f'Permission {permission_codename} not found')
                        )
                self.stdout.write(f'Assigned {len(group_data["permissions"])} permissions to {user_group.name}')
        
        # Create superuser if it doesn't exist
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@hospital.com',
                password='admin123',
                first_name='Super',
                last_name='Admin',
                role='admin'
            )
            self.stdout.write(self.style.SUCCESS('Created superuser: admin@hospital.com / admin123'))
        
        # Create sample users
        sample_users = [
            {
                'username': 'dr.smith', 'email': 'dr.smith@hospital.com', 'password': 'doctor123',
                'first_name': 'John', 'last_name': 'Smith', 'role': 'doctor',
                'department': 'Cardiology', 'employee_id': 'DOC001', 'group': 'Doctors'
            },
            {
                'username': 'nurse.jane', 'email': 'nurse.jane@hospital.com', 'password': 'nurse123',
                'first_name': 'Jane', 'last_name': 'Doe', 'role': 'nurse',
                'department': 'Emergency', 'employee_id': 'NUR001', 'group': 'Nurses'
            },
            {
                'username': 'receptionist.mary', 'email': 'mary@hospital.com', 'password': 'reception123',
                'first_name': 'Mary', 'last_name': 'Johnson', 'role': 'receptionist',
                'department': 'Front Desk', 'employee_id': 'REC001', 'group': 'Receptionists'
            }
        ]
        
        for user_data in sample_users:
            group_name = user_data.pop('group')
            if not User.objects.filter(email=user_data['email']).exists():
                user = User.objects.create_user(**user_data)
                group = Group.objects.get(name=group_name)
                user.groups.add(group)
                self.stdout.write(f'Created user: {user.email} / {user_data["password"]}')
        
        self.stdout.write(self.style.SUCCESS('Hospital management initial data created successfully!'))
        self.stdout.write(self.style.SUCCESS('You can now login with the following credentials:'))
        self.stdout.write('Superuser: admin@hospital.com / admin123')
        self.stdout.write('Doctor: dr.smith@hospital.com / doctor123')
        self.stdout.write('Nurse: nurse.jane@hospital.com / nurse123')
        self.stdout.write('Receptionist: mary@hospital.com / reception123')

# apps/permissions/management/commands/setup_permissions.py
from django.core.management.base import BaseCommand
from apps.permissions.models import Module, Permission

class Command(BaseCommand):
    help = 'Setup permissions for a specific module'
    
    def add_arguments(self, parser):
        parser.add_argument('module_name', type=str, help='Name of the module')
        parser.add_argument('--display-name', type=str, help='Display name of the module')
        parser.add_argument('--operations', nargs='+', default=['create', 'read', 'update', 'delete'],
                          help='Operations to create permissions for')
    
    def handle(self, *args, **options):
        module_name = options['module_name']
        display_name = options['display_name'] or module_name.title()
        operations = options['operations']
        
        # Create or get module
        module, created = Module.objects.get_or_create(
            name=module_name,
            defaults={'display_name': display_name}
        )
        
        if created:
            self.stdout.write(f'Created module: {module.display_name}')
        else:
            self.stdout.write(f'Module exists: {module.display_name}')
        
        # Create permissions
        created_permissions = []
        for operation in operations:
            permission, created = Permission.objects.get_or_create(
                module=module,
                operation=operation
            )
            if created:
                created_permissions.append(permission)
                self.stdout.write(f'Created permission: {permission.name}')
            else:
                self.stdout.write(f'Permission exists: {permission.name}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Setup complete! Created {len(created_permissions)} new permissions for {module.display_name}'
            )
        )

