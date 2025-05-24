from django.db import models

# Create your models here.
# apps/doctors/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
import datetime

User = get_user_model()

class Specialty(models.Model):
    """
    Medical specialties for doctors
    """
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True, help_text="Specialty code (e.g., CARD, NEURO)")
    description = models.TextField(blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'doctor_specialties'
        verbose_name = 'Specialty'
        verbose_name_plural = 'Specialties'
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Qualification(models.Model):
    """
    Educational qualifications for doctors
    """
    DEGREE_TYPES = [
        ('undergraduate', 'Undergraduate'),
        ('postgraduate', 'Postgraduate'),
        ('diploma', 'Diploma'),
        ('certificate', 'Certificate'),
        ('fellowship', 'Fellowship'),
        ('phd', 'PhD'),
    ]
    
    degree_name = models.CharField(max_length=200)
    degree_type = models.CharField(max_length=20, choices=DEGREE_TYPES)
    short_name = models.CharField(max_length=50, help_text="e.g., MBBS, MD, MS")
    description = models.TextField(blank=True, null=True)
    duration_years = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'doctor_qualifications'
        ordering = ['degree_type', 'degree_name']
    
    def __str__(self):
        return f"{self.short_name} - {self.degree_name}"

class Hospital(models.Model):
    """
    Hospitals where doctors have worked or are affiliated
    """
    name = models.CharField(max_length=200)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='India')
    pincode = models.CharField(max_length=10)
    phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    hospital_type = models.CharField(
        max_length=50,
        choices=[
            ('government', 'Government'),
            ('private', 'Private'),
            ('semi_government', 'Semi-Government'),
            ('trust', 'Trust'),
            ('corporate', 'Corporate'),
        ],
        default='private'
    )
    bed_capacity = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'hospitals'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name}, {self.city}"

class Doctor(models.Model):
    """
    Extended doctor profile linked to User model
    """
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]
    
    CONSULTATION_TYPES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('both', 'Both'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('on_leave', 'On Leave'),
        ('suspended', 'Suspended'),
        ('retired', 'Retired'),
    ]
    
    # Link to User model
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    
    # Personal Information
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    date_of_birth = models.DateField()
    age = models.PositiveIntegerField(editable=False)  # Calculated from date_of_birth
    
    # Contact Information
    mobile_primary = models.CharField(max_length=15)
    mobile_secondary = models.CharField(max_length=15, blank=True, null=True)
    email_primary = models.EmailField()
    email_secondary = models.EmailField(blank=True, null=True)
    
    # Address Information
    address_line1 = models.CharField(max_length=200)
    address_line2 = models.CharField(max_length=200, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='India')
    pincode = models.CharField(max_length=10)
    
    # Professional Information
    medical_license_number = models.CharField(max_length=50, unique=True)
    license_issuing_authority = models.CharField(max_length=200)
    license_issue_date = models.DateField()
    license_expiry_date = models.DateField()
    
    # Experience and Qualifications
    years_of_experience = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(60)]
    )
    specialties = models.ManyToManyField(
        Specialty, 
        through='DoctorSpecialty',
        related_name='doctors'
    )
    qualifications = models.ManyToManyField(
        Qualification,
        through='DoctorQualification',
        related_name='doctors'
    )
    
    # Consultation Information
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    consultation_duration = models.PositiveIntegerField(default=30, help_text="Duration in minutes")
    consultation_type = models.CharField(max_length=20, choices=CONSULTATION_TYPES, default='both')
    
    # Availability
    is_available_online = models.BooleanField(default=True)
    is_available_offline = models.BooleanField(default=True)
    
    # Professional Details
    bio = models.TextField(blank=True, null=True, help_text="Professional biography")
    languages_spoken = models.CharField(
        max_length=500, 
        blank=True, 
        null=True,
        help_text="Comma-separated languages"
    )
    
    # Ratings and Reviews
    average_rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    total_reviews = models.PositiveIntegerField(default=0)
    total_consultations = models.PositiveIntegerField(default=0)
    
    # Status and Metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    joining_date = models.DateField()
    profile_picture = models.ImageField(upload_to='doctors/profiles/', blank=True, null=True)
    signature = models.ImageField(upload_to='doctors/signatures/', blank=True, null=True)
    
    # Emergency Contact
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_relation = models.CharField(max_length=50, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'doctors'
        ordering = ['user__first_name', 'user__last_name']
        indexes = [
            models.Index(fields=['medical_license_number']),
            models.Index(fields=['status']),
            models.Index(fields=['city', 'state']),
        ]
    
    def __str__(self):
        return f"Dr. {self.user.get_full_name()}"
    
    def save(self, *args, **kwargs):
        # Calculate age from date_of_birth
        if self.date_of_birth:
            today = datetime.date.today()
            self.age = today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        super().save(*args, **kwargs)
    
    @property
    def full_name(self):
        return f"Dr. {self.user.get_full_name()}"
    
    @property
    def primary_specialty(self):
        """Get the primary (first) specialty"""
        specialty = self.doctorspecialty_set.filter(is_primary=True).first()
        return specialty.specialty if specialty else None
    
    @property
    def all_specialties(self):
        """Get all specialties as a comma-separated string"""
        specialties = self.specialties.filter(is_active=True)
        return ", ".join([s.name for s in specialties])
    
    @property
    def highest_qualification(self):
        """Get the highest qualification"""
        qual = self.doctorqualification_set.filter(
            qualification__is_active=True
        ).order_by('-year_completed').first()
        return qual.qualification if qual else None
    
    @property
    def is_license_valid(self):
        """Check if medical license is still valid"""
        return self.license_expiry_date > datetime.date.today()
    
    def get_absolute_url(self):
        return reverse('doctor-detail', kwargs={'pk': self.pk})

class DoctorSpecialty(models.Model):
    """
    Through model for Doctor-Specialty relationship with additional fields
    """
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    specialty = models.ForeignKey(Specialty, on_delete=models.CASCADE)
    is_primary = models.BooleanField(default=False, help_text="Primary specialty")
    years_of_experience = models.PositiveIntegerField(default=0)
    board_certified = models.BooleanField(default=False)
    certification_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'doctor_specialties_through'
        unique_together = ['doctor', 'specialty']
    
    def __str__(self):
        return f"{self.doctor.full_name} - {self.specialty.name}"

class DoctorQualification(models.Model):
    """
    Through model for Doctor-Qualification relationship with additional fields
    """
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    qualification = models.ForeignKey(Qualification, on_delete=models.CASCADE)
    institution_name = models.CharField(max_length=200)
    university_name = models.CharField(max_length=200)
    year_started = models.PositiveIntegerField()
    year_completed = models.PositiveIntegerField()
    grade_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    certificate_file = models.FileField(upload_to='doctors/certificates/', blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='verified_qualifications'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'doctor_qualifications_through'
        unique_together = ['doctor', 'qualification', 'institution_name']
        ordering = ['-year_completed']
    
    def __str__(self):
        return f"{self.doctor.full_name} - {self.qualification.short_name} ({self.year_completed})"

class DoctorExperience(models.Model):
    """
    Work experience of doctors at different hospitals/clinics
    """
    POSITION_TYPES = [
        ('intern', 'Intern'),
        ('resident', 'Resident'),
        ('fellow', 'Fellow'),
        ('consultant', 'Consultant'),
        ('senior_consultant', 'Senior Consultant'),
        ('head_of_department', 'Head of Department'),
        ('director', 'Director'),
        ('chief_medical_officer', 'Chief Medical Officer'),
    ]
    
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='experiences')
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)
    position = models.CharField(max_length=50, choices=POSITION_TYPES)
    department = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True, help_text="Leave blank if currently working")
    is_current = models.BooleanField(default=False)
    responsibilities = models.TextField(blank=True, null=True)
    achievements = models.TextField(blank=True, null=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'doctor_experiences'
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.doctor.full_name} - {self.position} at {self.hospital.name}"
    
    @property
    def duration_months(self):
        """Calculate duration in months"""
        end = self.end_date or datetime.date.today()
        return (end.year - self.start_date.year) * 12 + (end.month - self.start_date.month)

class DoctorAvailability(models.Model):
    """
    Doctor's availability schedule
    """
    DAYS_OF_WEEK = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]
    
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='availability')
    day_of_week = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    consultation_type = models.CharField(
        max_length=20, 
        choices=Doctor.CONSULTATION_TYPES,
        default='both'
    )
    max_patients = models.PositiveIntegerField(default=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'doctor_availability'
        unique_together = ['doctor', 'day_of_week', 'start_time']
        ordering = ['day_of_week', 'start_time']
    
    def __str__(self):
        return f"{self.doctor.full_name} - {self.get_day_of_week_display()} ({self.start_time}-{self.end_time})"

class DoctorReview(models.Model):
    """
    Patient reviews and ratings for doctors
    """
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='reviews')
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='doctor_reviews')
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    review_text = models.TextField(blank=True, null=True)
    consultation_date = models.DateField()
    is_verified = models.BooleanField(default=False)
    is_anonymous = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'doctor_reviews'
        unique_together = ['doctor', 'patient', 'consultation_date']
        ordering = ['-created_at']
    
    def __str__(self):
        patient_name = "Anonymous" if self.is_anonymous else self.patient.get_full_name()
        return f"{self.doctor.full_name} - {self.rating}★ by {patient_name}"