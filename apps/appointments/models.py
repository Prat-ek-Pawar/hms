# apps/appointments/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
import datetime
import uuid

User = get_user_model()

class AppointmentType(models.Model):
    """
    Different types of appointments (Consultation, Follow-up, Emergency, etc.)
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    duration_minutes = models.PositiveIntegerField(default=30, help_text="Default duration in minutes")
    color_code = models.CharField(max_length=7, default='#007bff', help_text="Hex color code for calendar display")
    is_active = models.BooleanField(default=True)
    requires_referral = models.BooleanField(default=False)
    is_emergency = models.BooleanField(default=False)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'appointment_types'
        ordering = ['name']
    
    def __str__(self):
        return self.name

class TimeSlot(models.Model):
    """
    Available time slots for appointments
    """
    DAYS_OF_WEEK = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    doctor = models.ForeignKey('doctors.Doctor', on_delete=models.CASCADE, related_name='time_slots')
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_duration = models.PositiveIntegerField(default=30, help_text="Duration of each slot in minutes")
    max_patients = models.PositiveIntegerField(default=1, help_text="Maximum patients per slot")
    is_available = models.BooleanField(default=True)
    
    # Special dates override
    date_override = models.DateField(null=True, blank=True, help_text="Override for specific date")
    is_holiday = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'time_slots'
        unique_together = ['doctor', 'day_of_week', 'start_time', 'date_override']
        ordering = ['day_of_week', 'start_time']
    
    def __str__(self):
        day_name = dict(self.DAYS_OF_WEEK)[self.day_of_week]
        if self.date_override:
            return f"Dr. {self.doctor.user.get_full_name()} - {self.date_override} ({self.start_time}-{self.end_time})"
        return f"Dr. {self.doctor.user.get_full_name()} - {day_name} ({self.start_time}-{self.end_time})"
    
    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError("End time must be after start time")

class Appointment(models.Model):
    """
    Main appointment model with comprehensive scheduling features
    """
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
        ('rescheduled', 'Rescheduled'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    # Core Information
    appointment_id = models.CharField(max_length=20, unique=True, editable=False)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey('doctors.Doctor', on_delete=models.CASCADE, related_name='appointments')
    appointment_type = models.ForeignKey(AppointmentType, on_delete=models.CASCADE)
    
    # Scheduling Details
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    duration_minutes = models.PositiveIntegerField(default=30)
    end_time = models.TimeField(editable=False)  # Auto-calculated
    
    # Status and Priority
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    
    # Appointment Details
    chief_complaint = models.TextField(help_text="Patient's main concern/reason for visit")
    symptoms = models.TextField(blank=True, null=True, help_text="Detailed symptoms")
    notes = models.TextField(blank=True, null=True, help_text="Additional notes")
    
    # Follow-up Information
    is_follow_up = models.BooleanField(default=False)
    parent_appointment = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='follow_up_appointments'
    )
    
    # Referral Information
    referred_by = models.CharField(max_length=200, blank=True, null=True, help_text="Referring doctor")
    referral_notes = models.TextField(blank=True, null=True)
    
    # Financial Information
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_paid = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    
    # Reminders and Notifications
    reminder_sent = models.BooleanField(default=False)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    sms_reminder = models.BooleanField(default=True)
    email_reminder = models.BooleanField(default=True)
    
    # Check-in Information
    checked_in_at = models.DateTimeField(null=True, blank=True)
    actual_start_time = models.TimeField(null=True, blank=True)
    actual_end_time = models.TimeField(null=True, blank=True)
    waiting_time_minutes = models.PositiveIntegerField(null=True, blank=True)
    
    # Cancellation/Rescheduling
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='cancelled_appointments'
    )
    cancellation_reason = models.TextField(blank=True, null=True)
    
    # Original appointment for rescheduled appointments
    original_appointment = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='rescheduled_appointments'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='created_appointments'
    )
    
    class Meta:
        db_table = 'appointments'
        ordering = ['appointment_date', 'appointment_time']
        indexes = [
            models.Index(fields=['appointment_id']),
            models.Index(fields=['appointment_date', 'appointment_time']),
            models.Index(fields=['doctor', 'appointment_date']),
            models.Index(fields=['patient', 'appointment_date']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.appointment_id} - {self.patient.full_name} with Dr. {self.doctor.user.get_full_name()}"
    
    def save(self, *args, **kwargs):
        # Generate appointment ID if not exists
        if not self.appointment_id:
            self.appointment_id = self.generate_appointment_id()
        
        # Calculate end time
        if self.appointment_time and self.duration_minutes:
            start_datetime = datetime.datetime.combine(datetime.date.today(), self.appointment_time)
            end_datetime = start_datetime + datetime.timedelta(minutes=self.duration_minutes)
            self.end_time = end_datetime.time()
        
        # Set consultation fee from appointment type if not set
        if not self.consultation_fee and self.appointment_type:
            self.consultation_fee = self.appointment_type.cost
        
        super().save(*args, **kwargs)
    
    def clean(self):
        # Validate appointment date is not in the past
        if self.appointment_date and self.appointment_date < timezone.now().date():
            if self.status == 'scheduled':
                raise ValidationError("Cannot schedule appointment in the past")
        
        # Validate doctor availability
        if self.doctor and self.appointment_date and self.appointment_time:
            day_of_week = self.appointment_date.weekday()
            if not self.doctor.time_slots.filter(
                day_of_week=day_of_week,
                start_time__lte=self.appointment_time,
                end_time__gte=self.appointment_time,
                is_available=True
            ).exists():
                raise ValidationError("Doctor is not available at this time")
    
    @classmethod
    def generate_appointment_id(cls):
        """Generate unique appointment ID"""
        current_year = datetime.datetime.now().year
        current_month = datetime.datetime.now().month
        
        # Get the last appointment created this month
        last_appointment = cls.objects.filter(
            appointment_id__startswith=f"APT{current_year}{current_month:02d}"
        ).order_by('-appointment_id').first()
        
        if last_appointment:
            # Extract number from last appointment ID and increment
            last_number = int(last_appointment.appointment_id[-4:])
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"APT{current_year}{current_month:02d}{new_number:04d}"
    
    @property
    def is_today(self):
        return self.appointment_date == timezone.now().date()
    
    @property
    def is_upcoming(self):
        now = timezone.now()
        appointment_datetime = datetime.datetime.combine(self.appointment_date, self.appointment_time)
        return appointment_datetime > now
    
    @property
    def is_past(self):
        now = timezone.now()
        appointment_datetime = datetime.datetime.combine(self.appointment_date, self.appointment_time)
        return appointment_datetime < now
    
    @property
    def time_until_appointment(self):
        """Returns timedelta until appointment"""
        now = timezone.now()
        appointment_datetime = datetime.datetime.combine(self.appointment_date, self.appointment_time)
        appointment_datetime = timezone.make_aware(appointment_datetime)
        return appointment_datetime - now
    
    @property
    def can_cancel(self):
        """Check if appointment can be cancelled (24 hours before)"""
        if self.status in ['completed', 'cancelled', 'no_show']:
            return False
        time_until = self.time_until_appointment
        return time_until.total_seconds() > 24 * 60 * 60  # 24 hours
    
    @property
    def can_reschedule(self):
        """Check if appointment can be rescheduled"""
        return self.can_cancel and self.status in ['scheduled', 'confirmed']
    
    def get_absolute_url(self):
        return reverse('appointment-detail', kwargs={'pk': self.pk})

class AppointmentReminder(models.Model):
    """
    Appointment reminders with different types and schedules
    """
    REMINDER_TYPES = [
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('push', 'Push Notification'),
        ('call', 'Phone Call'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='reminders')
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPES)
    scheduled_time = models.DateTimeField(help_text="When to send the reminder")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Message content
    subject = models.CharField(max_length=200, blank=True, null=True)
    message = models.TextField()
    
    # Delivery tracking
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'appointment_reminders'
        ordering = ['scheduled_time']
    
    def __str__(self):
        return f"{self.appointment.appointment_id} - {self.reminder_type} reminder"

class AppointmentAvailability(models.Model):
    """
    Real-time availability tracking for doctors
    """
    doctor = models.ForeignKey('doctors.Doctor', on_delete=models.CASCADE, related_name='availability_slots')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_duration = models.PositiveIntegerField(default=30, help_text="Duration in minutes")
    
    # Availability tracking
    total_slots = models.PositiveIntegerField(default=1)
    booked_slots = models.PositiveIntegerField(default=0)
    blocked_slots = models.PositiveIntegerField(default=0)  # Manually blocked by admin/doctor
    
    # Override settings
    is_available = models.BooleanField(default=True)
    reason_unavailable = models.CharField(max_length=200, blank=True, null=True)
    
    # Special pricing for this slot
    special_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'appointment_availability'
        unique_together = ['doctor', 'date', 'start_time']
        ordering = ['date', 'start_time']
    
    def __str__(self):
        return f"Dr. {self.doctor.user.get_full_name()} - {self.date} ({self.start_time}-{self.end_time})"
    
    @property
    def available_slots(self):
        return self.total_slots - self.booked_slots - self.blocked_slots
    
    @property
    def is_fully_booked(self):
        return self.available_slots <= 0
    
    @property
    def occupancy_percentage(self):
        if self.total_slots == 0:
            return 0
        return (self.booked_slots / self.total_slots) * 100

class WaitingList(models.Model):
    """
    Waiting list for appointments when no slots are available
    """
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('notified', 'Notified'),
        ('appointed', 'Appointed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]
    
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='waiting_list_entries')
    doctor = models.ForeignKey('doctors.Doctor', on_delete=models.CASCADE, related_name='waiting_list')
    appointment_type = models.ForeignKey(AppointmentType, on_delete=models.CASCADE)
    
    # Preferred scheduling
    preferred_date = models.DateField(null=True, blank=True)
    preferred_time_start = models.TimeField(null=True, blank=True)
    preferred_time_end = models.TimeField(null=True, blank=True)
    flexible_scheduling = models.BooleanField(default=True)
    
    # Priority and urgency
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    reason = models.TextField(help_text="Reason for appointment")
    urgency_notes = models.TextField(blank=True, null=True)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    notified_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Contact preferences
    contact_phone = models.CharField(max_length=15)
    contact_email = models.EmailField()
    sms_notifications = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'waiting_list'
        ordering = ['priority', 'created_at']
        indexes = [
            models.Index(fields=['doctor', 'status', 'priority']),
            models.Index(fields=['preferred_date']),
        ]
    
    def __str__(self):
        return f"{self.patient.full_name} waiting for Dr. {self.doctor.user.get_full_name()}"

class AppointmentFeedback(models.Model):
    """
    Patient feedback for completed appointments
    """
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='feedback')
    
    # Ratings (1-5 scale)
    overall_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    doctor_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    staff_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    facility_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    wait_time_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    
    # Feedback text
    positive_feedback = models.TextField(blank=True, null=True)
    improvement_suggestions = models.TextField(blank=True, null=True)
    additional_comments = models.TextField(blank=True, null=True)
    
    # Recommendation
    would_recommend = models.BooleanField(null=True)
    
    # Submission details
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_anonymous = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'appointment_feedback'
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"Feedback for {self.appointment.appointment_id} - {self.overall_rating}★"
