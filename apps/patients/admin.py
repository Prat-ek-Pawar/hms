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
    inlines = [PatientInsuranceInline, PatientAllergyInline, PatientMedicationInline, PatientDocumentInline]
    
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
                'allergies', 'chronic_conditions', 'current_medications',
                'past_surgeries', 'family_history'
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
            'fields': ('notes', 'profile_picture', 'created_by'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['patient_id', 'age', 'bmi', 'registration_date', 'created_by']
    
    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = 'Name'
    
    def insurance_status(self, obj):
        if obj.is_insurance_valid:
            return format_html('<span style="color: green;">✓ Valid</span>')
        elif obj.insurance_provider:
            return format_html('<span style="color: red;">✗ Expired</span>')
        else:
            return format_html('<span style="color: gray;">- No Insurance</span>')
    insurance_status.short_description = 'Insurance'
    
    actions = ['activate_patients', 'deactivate_patients', 'mark_as_transferred']
    
    def activate_patients(self, request, queryset):
        queryset.update(status='active')
        self.message_user(request, f'Activated {queryset.count()} patients')
    activate_patients.short_description = 'Activate selected patients'
    
    def deactivate_patients(self, request, queryset):
        queryset.update(status='inactive')
        self.message_user(request, f'Deactivated {queryset.count()} patients')
    deactivate_patients.short_description = 'Deactivate selected patients'
    
    def mark_as_transferred(self, request, queryset):
        queryset.update(status='transferred')
        self.message_user(request, f'Marked {queryset.count()} patients as transferred')
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
    
    def is_valid(self, obj):
        if obj.is_valid:
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

@admin.register(PatientVitals)
class PatientVitalsAdmin(admin.ModelAdmin):
    list_display = [
        'patient', 'temperature', 'blood_pressure', 'heart_rate',
        'weight', 'bmi', 'recorded_by', 'recorded_date'
    ]
    list_filter = ['recorded_date']
    search_fields = ['patient__first_name', 'patient__last_name']
    ordering = ['-recorded_date']
    
    def blood_pressure(self, obj):
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

@admin.register(PatientMedication)
class PatientMedicationAdmin(admin.ModelAdmin):
    list_display = [
        'patient', 'medication_name', 'dosage', 'frequency',
        'start_date', 'end_date', 'status', 'prescribed_by'
    ]
    list_filter = ['status', 'start_date', 'route']
    search_fields = [
        'patient__first_name', 'patient__last_name',
        'medication_name', 'prescribed_by'
    ]
    ordering = ['-start_date']

@admin.register(PatientNote)
class PatientNoteAdmin(admin.ModelAdmin):
    list_display = [
        'patient', 'note_type', 'title', 'created_by',
        'is_confidential', 'created_at'
    ]
    list_filter = ['note_type', 'is_confidential', 'created_at']
    search_fields = ['patient__first_name', 'patient__last_name', 'title', 'content']
    ordering = ['-created_at']