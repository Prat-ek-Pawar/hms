# apps/appointments/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta, time
from apps.patients.serializers import PatientListSerializer
from apps.doctors.serializers import DoctorListSerializer
from .models import (
    Appointment, AppointmentType, TimeSlot, AppointmentReminder,
    AppointmentAvailability, WaitingList, AppointmentFeedback
)

User = get_user_model()

class AppointmentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointmentType
        fields = [
            'id', 'name', 'description', 'duration_minutes', 'color_code',
            'is_active', 'requires_referral', 'is_emergency', 'cost',
            'created_at', 'updated_at'
        ]

class TimeSlotSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.user.get_full_name', read_only=True)
    day_name = serializers.SerializerMethodField()
    
    class Meta:
        model = TimeSlot
        fields = [
            'id', 'doctor', 'doctor_name', 'day_of_week', 'day_name',
            'start_time', 'end_time', 'slot_duration', 'max_patients',
            'is_available', 'date_override', 'is_holiday',
            'created_at', 'updated_at'
        ]
    
    def get_day_name(self, obj):
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return days[obj.day_of_week]

class AppointmentReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointmentReminder
        fields = [
            'id', 'reminder_type', 'scheduled_time', 'status',
            'subject', 'message', 'sent_at', 'delivered_at',
            'error_message', 'created_at', 'updated_at'
        ]

class AppointmentAvailabilitySerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.user.get_full_name', read_only=True)
    available_slots = serializers.ReadOnlyField()
    is_fully_booked = serializers.ReadOnlyField()
    occupancy_percentage = serializers.ReadOnlyField()
    
    class Meta:
        model = AppointmentAvailability
        fields = [
            'id', 'doctor', 'doctor_name', 'date', 'start_time', 'end_time',
            'slot_duration', 'total_slots', 'booked_slots', 'blocked_slots',
            'available_slots', 'is_fully_booked', 'occupancy_percentage',
            'is_available', 'reason_unavailable', 'special_fee',
            'created_at', 'updated_at'
        ]

class WaitingListSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.user.get_full_name', read_only=True)
    appointment_type_name = serializers.CharField(source='appointment_type.name', read_only=True)
    
    class Meta:
        model = WaitingList
        fields = [
            'id', 'patient', 'patient_name', 'doctor', 'doctor_name',
            'appointment_type', 'appointment_type_name', 'preferred_date',
            'preferred_time_start', 'preferred_time_end', 'flexible_scheduling',
            'priority', 'reason', 'urgency_notes', 'status',
            'contact_phone', 'contact_email', 'sms_notifications',
            'email_notifications', 'created_at', 'updated_at'
        ]

class AppointmentFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointmentFeedback
        fields = [
            'id', 'overall_rating', 'doctor_rating', 'staff_rating',
            'facility_rating', 'wait_time_rating', 'positive_feedback',
            'improvement_suggestions', 'additional_comments',
            'would_recommend', 'is_anonymous', 'submitted_at'
        ]

class AppointmentListSerializer(serializers.ModelSerializer):
    """Serializer for appointment list view with basic information"""
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    patient_phone = serializers.CharField(source='patient.mobile_primary', read_only=True)
    doctor_name = serializers.CharField(source='doctor.user.get_full_name', read_only=True)
    appointment_type_name = serializers.CharField(source='appointment_type.name', read_only=True)
    appointment_type_color = serializers.CharField(source='appointment_type.color_code', read_only=True)
    is_today = serializers.ReadOnlyField()
    is_upcoming = serializers.ReadOnlyField()
    can_cancel = serializers.ReadOnlyField()
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'appointment_id', 'patient', 'patient_name', 'patient_phone',
            'doctor', 'doctor_name', 'appointment_type', 'appointment_type_name',
            'appointment_type_color', 'appointment_date', 'appointment_time',
            'end_time', 'duration_minutes', 'status', 'priority',
            'chief_complaint', 'is_today', 'is_upcoming', 'can_cancel',
            'consultation_fee', 'is_paid', 'created_at'
        ]

class AppointmentDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for appointment with all related information"""
    patient = PatientListSerializer(read_only=True)
    doctor = DoctorListSerializer(read_only=True)
    appointment_type = AppointmentTypeSerializer(read_only=True)
    reminders = AppointmentReminderSerializer(many=True, read_only=True)
    feedback = AppointmentFeedbackSerializer(read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    cancelled_by_name = serializers.CharField(source='cancelled_by.get_full_name', read_only=True)
    
    # Computed fields
    is_today = serializers.ReadOnlyField()
    is_upcoming = serializers.ReadOnlyField()
    is_past = serializers.ReadOnlyField()
    can_cancel = serializers.ReadOnlyField()
    can_reschedule = serializers.ReadOnlyField()
    
    class Meta:
        model = Appointment
        fields = '__all__'

class AppointmentCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating appointments"""
    
    class Meta:
        model = Appointment
        exclude = ['appointment_id', 'end_time', 'created_by']
    
    def validate(self, attrs):
        # Validate appointment date is not in the past for new appointments
        if not self.instance and attrs.get('appointment_date'):
            if attrs['appointment_date'] < timezone.now().date():
                raise serializers.ValidationError("Cannot schedule appointment in the past")
        
        # Validate doctor availability
        doctor = attrs.get('doctor')
        appointment_date = attrs.get('appointment_date')
        appointment_time = attrs.get('appointment_time')
        
        if doctor and appointment_date and appointment_time:
            # Check if doctor has availability at this time
            day_of_week = appointment_date.weekday()
            if not doctor.time_slots.filter(
                day_of_week=day_of_week,
                start_time__lte=appointment_time,
                end_time__gte=appointment_time,
                is_available=True
            ).exists():
                raise serializers.ValidationError("Doctor is not available at this time")
            
            # Check for conflicting appointments
            duration = attrs.get('duration_minutes', 30)
            end_time = (datetime.combine(appointment_date, appointment_time) + 
                       timedelta(minutes=duration)).time()
            
            conflicting_appointments = Appointment.objects.filter(
                doctor=doctor,
                appointment_date=appointment_date,
                status__in=['scheduled', 'confirmed', 'in_progress'],
                appointment_time__lt=end_time,
                end_time__gt=appointment_time
            )
            
            if self.instance:
                conflicting_appointments = conflicting_appointments.exclude(pk=self.instance.pk)
            
            if conflicting_appointments.exists():
                raise serializers.ValidationError("Doctor has a conflicting appointment at this time")
        
        return attrs
    
    def create(self, validated_data):
        # Set duration from appointment type if not provided
        if not validated_data.get('duration_minutes') and validated_data.get('appointment_type'):
            validated_data['duration_minutes'] = validated_data['appointment_type'].duration_minutes
        
        return Appointment.objects.create(**validated_data)

class CalendarEventSerializer(serializers.ModelSerializer):
    """Serializer for calendar view with minimal data"""
    title = serializers.SerializerMethodField()
    start = serializers.SerializerMethodField()
    end = serializers.SerializerMethodField()
    color = serializers.CharField(source='appointment_type.color_code', read_only=True)
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'appointment_id', 'title', 'start', 'end', 'color',
            'status', 'priority', 'chief_complaint'
        ]
    
    def get_title(self, obj):
        return f"{obj.patient.full_name} - {obj.appointment_type.name}"
    
    def get_start(self, obj):
        return datetime.combine(obj.appointment_date, obj.appointment_time).isoformat()
    
    def get_end(self, obj):
        return datetime.combine(obj.appointment_date, obj.end_time).isoformat()