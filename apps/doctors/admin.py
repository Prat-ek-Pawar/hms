from django.contrib import admin

# Register your models here.
# apps/doctors/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Avg, Count
from .models import (
    Doctor, Specialty, Qualification, Hospital, DoctorSpecialty,
    DoctorQualification, DoctorExperience, DoctorAvailability, DoctorReview
)

@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'department', 'doctors_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'department', 'created_at']
    search_fields = ['name', 'code', 'description']
    ordering = ['name']
    actions = ['activate_specialties', 'deactivate_specialties']
    
    def doctors_count(self, obj):
        count = obj.doctors.filter(status='active').count()
        url = reverse('admin:doctors_doctor_changelist') + f'?specialties__id__exact={obj.id}'
        return format_html('<a href="{}">{} doctors</a>', url, count)
    doctors_count.short_description = 'Active Doctors'
    
    def activate_specialties(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f'Activated {queryset.count()} specialties')
    activate_specialties.short_description = 'Activate selected specialties'
    
    def deactivate_specialties(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f'Deactivated {queryset.count()} specialties')
    deactivate_specialties.short_description = 'Deactivate selected specialties'

@admin.register(Qualification)
class QualificationAdmin(admin.ModelAdmin):
    list_display = ['short_name', 'degree_name', 'degree_type', 'duration_years', 'is_active']
    list_filter = ['degree_type', 'is_active', 'created_at']
    search_fields = ['degree_name', 'short_name']
    ordering = ['degree_type', 'degree_name']

@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'state', 'hospital_type', 'bed_capacity', 'is_active']
    list_filter = ['hospital_type', 'state', 'is_active', 'created_at']
    search_fields = ['name', 'city', 'state']
    ordering = ['name']

class DoctorSpecialtyInline(admin.TabularInline):
    model = DoctorSpecialty
    extra = 1
    fields = ['specialty', 'is_primary', 'years_of_experience', 'board_certified', 'certification_date']

class DoctorQualificationInline(admin.TabularInline):
    model = DoctorQualification
    extra = 1
    fields = [
        'qualification', 'institution_name', 'university_name',
        'year_started', 'year_completed', 'grade_percentage', 'is_verified'
    ]

class DoctorExperienceInline(admin.TabularInline):
    model = DoctorExperience
    extra = 0
    fields = ['hospital', 'position', 'department', 'start_date', 'end_date', 'is_current']

class DoctorAvailabilityInline(admin.TabularInline):
    model = DoctorAvailability
    extra = 0
    fields = ['day_of_week', 'start_time', 'end_time', 'consultation_type', 'max_patients', 'is_available']

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = [
        'full_name', 'user_email', 'primary_specialty_display', 'years_of_experience',
        'consultation_fee', 'average_rating', 'status', 'is_license_valid'
    ]
    list_filter = [
        'status', 'gender', 'consultation_type', 'city', 'state',
        'is_available_online', 'is_available_offline', 'created_at'
    ]
    search_fields = [
        'user__first_name', 'user__last_name', 'user__email',
        'medical_license_number', 'mobile_primary'
    ]
    ordering = ['user__first_name', 'user__last_name']
    inlines = [DoctorSpecialtyInline, DoctorQualificationInline, DoctorExperienceInline, DoctorAvailabilityInline]
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Personal Information', {
            'fields': (
                'gender', 'date_of_birth', 'mobile_primary', 'mobile_secondary',
                'email_primary', 'email_secondary'
            )
        }),
        ('Address Information', {
            'fields': (
                'address_line1', 'address_line2', 'city', 'state', 'country', 'pincode'
            )
        }),
        ('Professional Information', {
            'fields': (
                'medical_license_number', 'license_issuing_authority',
                'license_issue_date', 'license_expiry_date', 'years_of_experience'
            )
        }),
        ('Consultation Information', {
            'fields': (
                'consultation_fee', 'consultation_duration', 'consultation_type',
                'is_available_online', 'is_available_offline'
            )
        }),
        ('Additional Information', {
            'fields': (
                'bio', 'languages_spoken', 'status', 'joining_date',
                'profile_picture', 'signature'
            )
        }),
        ('Emergency Contact', {
            'fields': (
                'emergency_contact_name', 'emergency_contact_relation', 'emergency_contact_phone'
            )
        }),
        ('Statistics', {
            'fields': ('average_rating', 'total_reviews', 'total_consultations'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['age', 'average_rating', 'total_reviews', 'total_consultations']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'
    
    def primary_specialty_display(self, obj):
        primary = obj.primary_specialty
        if primary:
            return format_html('<span title="{}">{}</span>', primary.description or '', primary.name)
        return 'No specialty'
    primary_specialty_display.short_description = 'Primary Specialty'
    
    def is_license_valid(self, obj):
        is_valid = obj.is_license_valid
        color = 'green' if is_valid else 'red'
        status = 'Valid' if is_valid else 'Expired'
        return format_html('<span style="color: {};">{}</span>', color, status)
    is_license_valid.short_description = 'License Status'
    
    actions = ['activate_doctors', 'deactivate_doctors', 'mark_on_leave']
    
    def activate_doctors(self, request, queryset):
        queryset.update(status='active')
        self.message_user(request, f'Activated {queryset.count()} doctors')
    activate_doctors.short_description = 'Activate selected doctors'
    
    def deactivate_doctors(self, request, queryset):
        queryset.update(status='inactive')
        self.message_user(request, f'Deactivated {queryset.count()} doctors')
    deactivate_doctors.short_description = 'Deactivate selected doctors'
    
    def mark_on_leave(self, request, queryset):
        queryset.update(status='on_leave')
        self.message_user(request, f'Marked {queryset.count()} doctors as on leave')
    mark_on_leave.short_description = 'Mark as on leave'

@admin.register(DoctorExperience)
class DoctorExperienceAdmin(admin.ModelAdmin):
    list_display = ['doctor', 'hospital', 'position', 'department', 'start_date', 'end_date', 'is_current']
    list_filter = ['position', 'is_current', 'start_date']
    search_fields = ['doctor__user__first_name', 'doctor__user__last_name', 'hospital__name']
    ordering = ['-start_date']

@admin.register(DoctorAvailability)
class DoctorAvailabilityAdmin(admin.ModelAdmin):
    list_display = ['doctor', 'day_of_week', 'start_time', 'end_time', 'consultation_type', 'max_patients', 'is_available']
    list_filter = ['day_of_week', 'consultation_type', 'is_available']
    search_fields = ['doctor__user__first_name', 'doctor__user__last_name']
    ordering = ['doctor', 'day_of_week', 'start_time']

@admin.register(DoctorReview)
class DoctorReviewAdmin(admin.ModelAdmin):
    list_display = ['doctor', 'patient_name', 'rating', 'consultation_date', 'is_verified', 'created_at']
    list_filter = ['rating', 'is_verified', 'is_anonymous', 'created_at']
    search_fields = ['doctor__user__first_name', 'doctor__user__last_name', 'patient__first_name', 'patient__last_name']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    def patient_name(self, obj):
        return "Anonymous" if obj.is_anonymous else obj.patient.get_full_name()
    patient_name.short_description = 'Patient'