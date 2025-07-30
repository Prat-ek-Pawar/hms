# apps/permissions/management/commands/create_permissions.py

from django.core.management.base import BaseCommand
from django.apps import apps
from apps.permissions.models import Permission, PermissionManager

class Command(BaseCommand):
    help = 'Create permissions for all models or specific app/model'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--app',
            type=str,
            help='Create permissions for specific app'
        )
        parser.add_argument(
            '--model',
            type=str,
            help='Create permissions for specific model (requires --app)'
        )
        parser.add_argument(
            '--operations',
            nargs='+',
            default=['create', 'read', 'update', 'delete'],
            help='Operations to create permissions for'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Create permissions for all apps'
        )
    
    def handle(self, *args, **options):
        app_label = options.get('app')
        model_name = options.get('model')
        operations = options.get('operations')
        create_all = options.get('all')
        
        if create_all:
            # Create permissions for all apps
            self.stdout.write("Creating permissions for all apps...")
            created_permissions = PermissionManager.create_all_permissions()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created {len(created_permissions)} permissions')
            )
            
        elif app_label and model_name:
            # Create permissions for specific model
            try:
                model_class = apps.get_model(app_label, model_name)
                created_permissions = Permission.create_permissions_for_model(model_class, operations)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully created {len(created_permissions)} permissions for {model_class._meta.verbose_name}'
                    )
                )
            except LookupError:
                self.stdout.write(
                    self.style.ERROR(f'Model {model_name} not found in app {app_label}')
                )
                
        elif app_label:
            # Create permissions for specific app
            try:
                created_permissions = PermissionManager.create_permissions_for_app(app_label, operations)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully created {len(created_permissions)} permissions for app {app_label}'
                    )
                )
            except LookupError:
                self.stdout.write(
                    self.style.ERROR(f'App {app_label} not found')
                )
        else:
            self.stdout.write(
                self.style.ERROR('Please specify --app, --model, or --all')
            )
        
        # Show created permissions
        if 'created_permissions' in locals():
            for perm in created_permissions:
                self.stdout.write(f"  - {perm.codename}: {perm.name}")

