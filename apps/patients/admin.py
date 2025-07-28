# apps/patients/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from .models import (
    Patient, PatientInsurance, PatientDocument, PatientVitals,
    PatientAllergy, PatientMedication, PatientNote
)

class PatientInsuranceInline(admin.TabularInline):
    model = PatientInsurance
    extra = 0
    fields = ['provider_name', 'policy_number', 'policy_type', 'coverage_amount', 'start_date', 'expiry_date', 'status']

class PatientAllergyInline(admin.TabularInline):
    model = PatientAllergy
    extra = 0
    fields = ['allergy_type', 'allergen', 'severity', 'symptoms', 'is_active']

class PatientMedicationInline(admin.TabularInline):
    model = PatientMedication
    extra = 0
    fields = ['medication_name', 'dosage', 'frequency', 'start_date', 'status']

class PatientDocumentInline(admin.TabularInline):
    model = PatientDocument
    extra = 0
    fields = ['document_type', 'title', 'document_date', 'is_sensitive']
    readonly_fields = ['document_date']

class PatientNoteInline(admin.TabularInline):
    model = PatientNote
    extra = 0
    fields = ['note_type', 'title', 'content', 'is_confidential']

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = [
        'patient_id', 'full_name', 'gender', 'age', 'mobile_primary',
        'city', 'blood_group', 'patient_type', 'status', 'total_visits',
        'registration_date', 'insurance_status'
    ]
    list_filter = [
        'status', 'gender', 'blood_group', 'patient_type', 'marital_status',
        'city', 'state', 'registration_date'
    ]
    search_fields = [
        'patient_id', 'first_name', 'last_name', 'mobile_primary',
        'email', 'emergency_contact_name'
    ]
    ordering = ['-registration_date']
    inlines = [
        PatientInsuranceInline,
        PatientAllergyInline,
        PatientMedicationInline,
        PatientDocumentInline,
        PatientNoteInline
    ]

    fieldsets = (
        ('Patient Information', {
            'fields': ('patient_id', 'user', 'status')
        }),
        ('Personal Information', {
            'fields': (
                ('first_name', 'middle_name', 'last_name'),
                ('gender', 'date_of_birth', 'age'),
                ('mobile_primary', 'mobile_secondary', 'email')
            )
        }),
        ('Address Information', {
            'fields': (
                'address_line1', 'address_line2',
                ('city', 'state', 'pincode'),
                'country'
            )
        }),
        ('Medical Information', {
            'fields': (
                ('blood_group', 'height', 'weight', 'bmi'),
                'chronic_conditions', 'past_surgeries', 'family_history'
            )
        }),
        ('Social Information', {
            'fields': (
                ('marital_status', 'occupation', 'education'),
                ('religion', 'nationality', 'languages_spoken')
            )
        }),
        ('Emergency Contact', {
            'fields': (
                'emergency_contact_name', 'emergency_contact_relation',
                'emergency_contact_phone', 'emergency_contact_address'
            )
        }),
        ('Insurance Information', {
            'fields': (
                'insurance_provider', 'insurance_policy_number', 'insurance_expiry_date'
            )
        }),
        ('Hospital Information', {
            'fields': (
                'patient_type', 'registration_date', 'last_visit_date', 'total_visits'
            )
        }),
        ('Additional Information', {
            'fields': ('profile_picture', 'created_by'),
            'classes': ('collapse',)
        })
    )

    readonly_fields = ['patient_id', 'age', 'bmi', 'registration_date', 'created_by']

    def get_queryset(self, request):
        """Optimize queryset with related objects"""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'created_by').prefetch_related(
            'patientallergy_set',
            'patientmedication_set',
            'patientnote_set',
            'patientinsurance_set'
        )

    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = 'Name'

    def insurance_status(self, obj):
        """Display insurance status with color coding"""
        if hasattr(obj, 'is_insurance_valid') and obj.is_insurance_valid:
            return format_html('<span style="color: green;">✓ Valid</span>')
        elif obj.insurance_provider:
            return format_html('<span style="color: red;">✗ Expired</span>')
        else:
            return format_html('<span style="color: gray;">- No Insurance</span>')
    insurance_status.short_description = 'Insurance'

    def total_allergies(self, obj):
        """Count of active allergies"""
        return obj.patientallergy_set.filter(is_active=True).count()
    total_allergies.short_description = 'Active Allergies'

    def total_medications(self, obj):
        """Count of current medications"""
        return obj.patientmedication_set.filter(status='active').count()
    total_medications.short_description = 'Current Medications'

    actions = ['activate_patients', 'deactivate_patients', 'mark_as_transferred']

    def activate_patients(self, request, queryset):
        updated = queryset.update(status='active')
        self.message_user(request, f'Activated {updated} patients')
    activate_patients.short_description = 'Activate selected patients'

    def deactivate_patients(self, request, queryset):
        updated = queryset.update(status='inactive')
        self.message_user(request, f'Deactivated {updated} patients')
    deactivate_patients.short_description = 'Deactivate selected patients'

    def mark_as_transferred(self, request, queryset):
        updated = queryset.update(status='transferred')
        self.message_user(request, f'Marked {updated} patients as transferred')
    mark_as_transferred.short_description = 'Mark as transferred'

@admin.register(PatientInsurance)
class PatientInsuranceAdmin(admin.ModelAdmin):
    list_display = [
        'patient', 'provider_name', 'policy_number', 'policy_type',
        'coverage_amount', 'start_date', 'expiry_date', 'status', 'is_valid'
    ]
    list_filter = ['status', 'policy_type', 'provider_name', 'start_date']
    search_fields = ['patient__first_name', 'patient__last_name', 'policy_number', 'provider_name']
    ordering = ['-start_date']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('patient')

    def is_valid(self, obj):
        if hasattr(obj, 'is_valid') and obj.is_valid:
            return format_html('<span style="color: green;">✓ Valid</span>')
        else:
            return format_html('<span style="color: red;">✗ Invalid</span>')
    is_valid.short_description = 'Status'

@admin.register(PatientDocument)
class PatientDocumentAdmin(admin.ModelAdmin):
    list_display = [
        'patient', 'document_type', 'title', 'document_date',
        'uploaded_by', 'is_sensitive', 'created_at'
    ]
    list_filter = ['document_type', 'is_sensitive', 'document_date', 'created_at']
    search_fields = ['patient__first_name', 'patient__last_name', 'title', 'description']
    ordering = ['-document_date']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('patient', 'uploaded_by')

@admin.register(PatientVitals)
class PatientVitalsAdmin(admin.ModelAdmin):
    list_display = [
        'patient', 'temperature', 'blood_pressure', 'heart_rate',
        'weight', 'bmi', 'recorded_by', 'recorded_date'
    ]
    list_filter = ['recorded_date']
    search_fields = ['patient__first_name', 'patient__last_name']
    ordering = ['-recorded_date']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('patient', 'recorded_by')

    def blood_pressure(self, obj):
        if hasattr(obj, 'blood_pressure_systolic') and hasattr(obj, 'blood_pressure_diastolic'):
            if obj.blood_pressure_systolic and obj.blood_pressure_diastolic:
                return f"{obj.blood_pressure_systolic}/{obj.blood_pressure_diastolic}"
        return "-"
    blood_pressure.short_description = 'BP (mmHg)'

@admin.register(PatientAllergy)
class PatientAllergyAdmin(admin.ModelAdmin):
    list_display = [
        'patient', 'allergy_type', 'allergen', 'severity',
        'is_active', 'onset_date', 'created_at'
    ]
    list_filter = ['allergy_type', 'severity', 'is_active', 'created_at']
    search_fields = ['patient__first_name', 'patient__last_name', 'allergen', 'symptoms']
    ordering = ['-severity', 'allergen']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('patient')

@admin.register(PatientMedication)
class PatientMedicationAdmin(admin.ModelAdmin):
    list_display = [
        'patient', 'medication_name', 'dosage', 'frequency',
        'start_date', 'end_date', 'status', 'prescribed_by'
    ]
    list_filter = ['status', 'start_date']
    search_fields = [
        'patient__first_name', 'patient__last_name',
        'medication_name', 'prescribed_by'
    ]
    ordering = ['-start_date']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('patient')

    # Only include 'route' filter if the field exists in the model
    # list_filter = ['status', 'start_date', 'route']  # Uncomment if route field exists

@admin.register(PatientNote)
class PatientNoteAdmin(admin.ModelAdmin):
    list_display = [
        'patient', 'note_type', 'title', 'created_by',
        'is_confidential', 'created_at'
    ]
    list_filter = ['note_type', 'is_confidential', 'created_at']
    search_fields = ['patient__first_name', 'patient__last_name', 'title', 'content']
    ordering = ['-created_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('patient', 'created_by')
