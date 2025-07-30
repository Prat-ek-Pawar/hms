# Usage examples in your apps/appointments/management/commands/setup_appointments.py
from django.core.management.base import BaseCommand
from apps.permissions.models import Permission
from apps.appointments.models import Appointment, Doctor, TimeSlot

class Command(BaseCommand):
    help = 'Setup permissions for appointments app'
    
    def handle(self, *args, **options):
        # Auto-create standard CRUD permissions
        models = [Appointment, Doctor, TimeSlot]
        
        for model in models:
            created = Permission.create_permissions_for_model(model)
            self.stdout.write(f"Created {len(created)} permissions for {model._meta.verbose_name}")
        
        # Create custom permissions
        custom_permissions = [
            (Appointment, 'approve', 'Can approve appointments'),
            (Appointment, 'cancel', 'Can cancel appointments'),
            (Doctor, 'schedule', 'Can manage doctor schedules'),
        ]
        
        for model, operation, description in custom_permissions:
            perm, created = Permission.objects.get_or_create(
                content_type=ContentType.objects.get_for_model(model),
                operation=operation,
                defaults={'description': description}
            )
            if created:
                self.stdout.write(f"Created custom permission: {perm.codename}")
        
        self.stdout.write(self.style.SUCCESS('Appointments permissions setup complete!'))