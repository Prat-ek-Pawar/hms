# apps/appointments/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Avg
from django.utils import timezone
from .models import (
    Appointment, AppointmentType, TimeSlot, AppointmentReminder,
    AppointmentAvailability, WaitingList, AppointmentFeedback
)

@admin.register(AppointmentType)
class AppointmentTypeAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'duration_minutes', 'cost', 'color_display', 
        'is_active', 'requires_referral', 'is_emergency'
    ]
    list_filter = ['is_active', 'requires_referral', 'is_emergency', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']
    
    def color_display(self, obj):
        return format_html(
            '<div style="width: 30px; height: 20px; background-color: {}; border: 1px solid #ccc;"></div>',
            obj.color_code
        )
    color_display.short_description = 'Color'

@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = [
        'doctor', 'day_name', 'start_time', 'end_time', 
        'slot_duration', 'max_patients', 'is_available'
    ]
    list_filter = ['day_of_week', 'is_available', 'is_holiday']
    search_fields = ['doctor__user__first_name', 'doctor__user__last_name']
    ordering = ['doctor', 'day_of_week', 'start_time']
    
    def day_name(self, obj):
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return days[obj.day_of_week]
    day_name.short_description = 'Day'

class AppointmentReminderInline(admin.TabularInline):
    model = AppointmentReminder
    extra = 0
    fields = ['reminder_type', 'scheduled_time', 'status', 'sent_at']
    readonly_fields = ['sent_at']

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = [
        'appointment_id', 'patient_name', 'doctor_name', 'appointment_type',
        'appointment_date', 'appointment_time', 'status_display', 'priority',
        'is_paid', 'created_at'
    ]
    list_filter = [
        'status', 'priority', 'appointment_type', 'is_follow_up',
        'is_paid', 'appointment_date', 'created_at'
    ]
    search_fields = [
        'appointment_id', 'patient__first_name', 'patient__last_name',
        'doctor__user__first_name', 'doctor__user__last_name',
        'chief_complaint'
    ]
    ordering = ['-appointment_date', '-appointment_time']
    inlines = [AppointmentReminderInline]
    
    fieldsets = (
        ('Appointment Information', {
            'fields': (
                'appointment_id', 'patient', 'doctor', 'appointment_type',
                ('appointment_date', 'appointment_time', 'duration_minutes'),
                ('status', 'priority')
            )
        }),
        ('Medical Information', {
            'fields': ('chief_complaint', 'symptoms', 'notes', 'is_follow_up', 'parent_appointment')
        }),
        ('Referral Information', {
            'fields': ('referred_by', 'referral_notes'),
            'classes': ('collapse',)
        }),
        ('Financial Information', {
            'fields': ('consultation_fee', 'is_paid', 'payment_method')
        }),
        ('Check-in Information', {
            'fields': (
                'checked_in_at', 'actual_start_time', 'actual_end_time',
                'waiting_time_minutes'
            ),
            'classes': ('collapse',)
        }),
        ('Cancellation/Rescheduling', {
            'fields': (
                'cancelled_at', 'cancelled_by', 'cancellation_reason',
                'original_appointment'
            ),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = [
        'appointment_id', 'end_time', 'created_at', 'updated_at'
    ]
    
    def patient_name(self, obj):
        return obj.patient.full_name
    patient_name.short_description = 'Patient'
    
    def doctor_name(self, obj):
        return f"Dr. {obj.doctor.user.get_full_name()}"
    doctor_name.short_description = 'Doctor'
    
    def status_display(self, obj):
        colors = {
            'scheduled': '#17a2b8',
            'confirmed': '#28a745',
            'in_progress': '#ffc107',
            'completed': '#6c757d',
            'cancelled': '#dc3545',
            'no_show': '#fd7e14',
            'rescheduled': '#6f42c1'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    actions = ['mark_confirmed', 'mark_completed', 'mark_cancelled']
    
    def mark_confirmed(self, request, queryset):
        queryset.filter(status='scheduled').update(status='confirmed')
        self.message_user(request, f'Marked {queryset.count()} appointments as confirmed')
    mark_confirmed.short_description = 'Mark selected appointments as confirmed'
    
    def mark_completed(self, request, queryset):
        queryset.filter(status__in=['confirmed', 'in_progress']).update(status='completed')
        self.message_user(request, f'Marked {queryset.count()} appointments as completed')
    mark_completed.short_description = 'Mark selected appointments as completed'
    
    def mark_cancelled(self, request, queryset):
        queryset.filter(status__in=['scheduled', 'confirmed']).update(
            status='cancelled',
            cancelled_at=timezone.now(),
            cancelled_by=request.user
        )
        self.message_user(request, f'Cancelled {queryset.count()} appointments')
    mark_cancelled.short_description = 'Cancel selected appointments'

@admin.register(AppointmentAvailability)
class AppointmentAvailabilityAdmin(admin.ModelAdmin):
    list_display = [
        'doctor', 'date', 'start_time', 'end_time', 'total_slots',
        'booked_slots', 'available_slots', 'occupancy_display', 'is_available'
    ]
    list_filter = ['date', 'is_available', 'doctor']
    search_fields = ['doctor__user__first_name', 'doctor__user__last_name']
    ordering = ['-date', 'start_time']
    
    def occupancy_display(self, obj):
        percentage = obj.occupancy_percentage
        if percentage >= 90:
            color = '#dc3545'  # Red
        elif percentage >= 70:
            color = '#ffc107'  # Yellow
        else:
            color = '#28a745'  # Green
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color, percentage
        )
    occupancy_display.short_description = 'Occupancy'

@admin.register(WaitingList)
class WaitingListAdmin(admin.ModelAdmin):
    list_display = [
        'patient', 'doctor', 'appointment_type', 'priority',
        'preferred_date', 'status', 'created_at'
    ]
    list_filter = ['status', 'priority', 'appointment_type', 'created_at']
    search_fields = [
        'patient__first_name', 'patient__last_name',
        'doctor__user__first_name', 'doctor__user__last_name'
    ]
    ordering = ['priority', 'created_at']
    
    actions = ['mark_notified', 'mark_appointed']
    
    def mark_notified(self, request, queryset):
        queryset.filter(status='active').update(
            status='notified',
            notified_at=timezone.now()
        )
        self.message_user(request, f'Marked {queryset.count()} entries as notified')
    mark_notified.short_description = 'Mark as notified'
    
    def mark_appointed(self, request, queryset):
        queryset.update(status='appointed')
        self.message_user(request, f'Marked {queryset.count()} entries as appointed')
    mark_appointed.short_description = 'Mark as appointed'

@admin.register(AppointmentFeedback)
class AppointmentFeedbackAdmin(admin.ModelAdmin):
    list_display = [
        'appointment', 'overall_rating', 'doctor_rating', 'would_recommend',
        'is_anonymous', 'submitted_at'
    ]
    list_filter = [
        'overall_rating', 'doctor_rating', 'would_recommend',
        'is_anonymous', 'submitted_at'
    ]
    search_fields = [
        'appointment__patient__first_name', 'appointment__patient__last_name',
        'appointment__doctor__user__first_name', 'appointment__doctor__user__last_name'
    ]
    ordering = ['-submitted_at']
    readonly_fields = ['submitted_at']

@admin.register(AppointmentReminder)
class AppointmentReminderAdmin(admin.ModelAdmin):
    list_display = [
        'appointment', 'reminder_type', 'scheduled_time', 'status',
        'sent_at', 'delivered_at'
    ]
    list_filter = ['reminder_type', 'status', 'scheduled_time']
    search_fields = [
        'appointment__appointment_id',
        'appointment__patient__first_name',
        'appointment__patient__last_name'
    ]
    ordering = ['-scheduled_time']
    readonly_fields = ['sent_at', 'delivered_at']