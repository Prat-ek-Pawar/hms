# apps/patients/models.py (FIXED VERSION)
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
import datetime
import uuid

User = get_user_model()

class Patient(models.Model):
    """
    Patient model with comprehensive medical and personal information
    """
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]
    
    BLOOD_GROUP_CHOICES = [
        ('A+', 'A+'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B-', 'B-'),
        ('AB+', 'AB+'),
        ('AB-', 'AB-'),
        ('O+', 'O+'),
        ('O-', 'O-'),
    ]
    
    MARITAL_STATUS_CHOICES = [
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
    ]
    
    PATIENT_TYPE_CHOICES = [
        ('inpatient', 'Inpatient'),
        ('outpatient', 'Outpatient'),
        ('emergency', 'Emergency'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('deceased', 'Deceased'),
        ('transferred', 'Transferred'),
    ]
    
    # Primary Identification
    patient_id = models.CharField(
        max_length=20, 
        unique=True, 
        editable=False,
        help_text="Auto-generated unique patient ID"
    )
    
    # Optional link to User model (for patients who have user accounts)
    user = models.OneToOneField(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='patient_profile'
    )
    
    # Personal Information
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    date_of_birth = models.DateField()
    age = models.PositiveIntegerField(editable=False)  # Auto-calculated
    
    # Contact Information
    mobile_primary = models.CharField(
        max_length=15,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Enter a valid phone number')]
    )
    mobile_secondary = models.CharField(
        max_length=15, 
        blank=True, 
        null=True,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Enter a valid phone number')]
    )
    email = models.EmailField(blank=True, null=True)
    
    # Address Information
    address_line1 = models.CharField(max_length=200)
    address_line2 = models.CharField(max_length=200, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='India')
    pincode = models.CharField(max_length=10)
    
    # Medical Information
    blood_group = models.CharField(max_length=5, choices=BLOOD_GROUP_CHOICES, blank=True, null=True)
    height = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Height in cm"
    )
    weight = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Weight in kg"
    )
    bmi = models.DecimalField(
        max_digits=4, 
        decimal_places=2, 
        null=True, 
        blank=True,
        editable=False,
        help_text="Auto-calculated BMI"
    )
    
    # Social Information
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS_CHOICES, default='single')
    occupation = models.CharField(max_length=100, blank=True, null=True)
    education = models.CharField(max_length=100, blank=True, null=True)
    religion = models.CharField(max_length=50, blank=True, null=True)
    nationality = models.CharField(max_length=50, default='Indian')
    languages_spoken = models.CharField(
        max_length=500, 
        blank=True, 
        null=True,
        help_text="Comma-separated languages"
    )
    
    # Emergency Contact
    emergency_contact_name = models.CharField(max_length=100)
    emergency_contact_relation = models.CharField(max_length=50)
    emergency_contact_phone = models.CharField(
        max_length=15,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Enter a valid phone number')]
    )
    emergency_contact_address = models.TextField(blank=True, null=True)
    
    # Medical History - RENAMED FIELDS TO AVOID CONFLICTS
    allergies_summary = models.TextField(blank=True, null=True, help_text="Known allergies summary")
    chronic_conditions = models.TextField(blank=True, null=True, help_text="Chronic medical conditions")
    medications_summary = models.TextField(blank=True, null=True, help_text="Current medications summary")
    past_surgeries = models.TextField(blank=True, null=True, help_text="Past surgical history")
    family_history = models.TextField(blank=True, null=True, help_text="Family medical history")
    
    # Insurance Information
    insurance_provider = models.CharField(max_length=200, blank=True, null=True)
    insurance_policy_number = models.CharField(max_length=100, blank=True, null=True)
    insurance_expiry_date = models.DateField(blank=True, null=True)
    
    # Hospital Information
    patient_type = models.CharField(max_length=20, choices=PATIENT_TYPE_CHOICES, default='outpatient')
    registration_date = models.DateTimeField(auto_now_add=True)
    last_visit_date = models.DateTimeField(blank=True, null=True)
    total_visits = models.PositiveIntegerField(default=0)
    
    # Status and Additional Info
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    general_notes = models.TextField(blank=True, null=True, help_text="General notes about patient")
    profile_picture = models.ImageField(upload_to='patients/profiles/', blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='created_patients'
    )
    
    class Meta:
        db_table = 'patients'
        ordering = ['-registration_date']
        indexes = [
            models.Index(fields=['patient_id']),
            models.Index(fields=['mobile_primary']),
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['city', 'state']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.full_name} ({self.patient_id})"
    
    def save(self, *args, **kwargs):
        # Generate patient ID if not exists
        if not self.patient_id:
            self.patient_id = self.generate_patient_id()
        
        # Calculate age from date_of_birth
        if self.date_of_birth:
            today = datetime.date.today()
            self.age = today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        
        # Calculate BMI if height and weight are provided
        if self.height and self.weight:
            height_m = float(self.height) / 100  # Convert cm to meters
            self.bmi = float(self.weight) / (height_m ** 2)
        
        super().save(*args, **kwargs)
    
    @property
    def full_name(self):
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_address(self):
        address_parts = [self.address_line1]
        if self.address_line2:
            address_parts.append(self.address_line2)
        address_parts.extend([self.city, self.state, self.pincode])
        return ", ".join(address_parts)
    
    @property
    def is_insurance_valid(self):
        if not self.insurance_expiry_date:
            return False
        return self.insurance_expiry_date > datetime.date.today()
    
    @classmethod
    def generate_patient_id(cls):
        """Generate unique patient ID"""
        current_year = datetime.datetime.now().year
        
        # Get the last patient created this year
        last_patient = cls.objects.filter(
            patient_id__startswith=f"PAT{current_year}"
        ).order_by('-patient_id').first()
        
        if last_patient:
            # Extract number from last patient ID and increment
            last_number = int(last_patient.patient_id[-4:])
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"PAT{current_year}{new_number:04d}"
    
    def get_absolute_url(self):
        return reverse('patient-detail', kwargs={'pk': self.pk})

class PatientInsurance(models.Model):
    """
    Multiple insurance policies for a patient
    """
    POLICY_STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='insurance_policies')
    provider_name = models.CharField(max_length=200)
    policy_number = models.CharField(max_length=100, unique=True)
    policy_type = models.CharField(max_length=100, help_text="e.g., Health, Life, Accident")
    coverage_amount = models.DecimalField(max_digits=12, decimal_places=2)
    premium_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    start_date = models.DateField()
    expiry_date = models.DateField()
    status = models.CharField(max_length=20, choices=POLICY_STATUS_CHOICES, default='active')
    
    # Coverage details
    covered_treatments = models.TextField(blank=True, null=True, help_text="List of covered treatments")
    excluded_treatments = models.TextField(blank=True, null=True, help_text="List of excluded treatments")
    
    # Documents
    policy_document = models.FileField(upload_to='patients/insurance/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'patient_insurance'
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.provider_name} ({self.policy_number})"
    
    @property
    def is_valid(self):
        return self.expiry_date > datetime.date.today() and self.status == 'active'

class PatientDocument(models.Model):
    """
    Patient documents and files
    """
    DOCUMENT_TYPES = [
        ('id_proof', 'ID Proof'),
        ('address_proof', 'Address Proof'),
        ('insurance', 'Insurance Document'),
        ('medical_report', 'Medical Report'),
        ('prescription', 'Prescription'),
        ('lab_report', 'Lab Report'),
        ('xray', 'X-Ray'),
        ('scan', 'CT/MRI Scan'),
        ('discharge_summary', 'Discharge Summary'),
        ('other', 'Other'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    document_file = models.FileField(upload_to='patients/documents/')
    document_date = models.DateField(default=datetime.date.today)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    is_sensitive = models.BooleanField(default=False, help_text="Sensitive medical information")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'patient_documents'
        ordering = ['-document_date']
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.title}"

class PatientVitals(models.Model):
    """
    Patient vital signs recorded during visits
    """
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='vitals')
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    recorded_date = models.DateTimeField(auto_now_add=True)
    
    # Vital signs
    temperature = models.DecimalField(
        max_digits=4, 
        decimal_places=1, 
        null=True, 
        blank=True,
        help_text="Temperature in Celsius"
    )
    blood_pressure_systolic = models.PositiveIntegerField(null=True, blank=True)
    blood_pressure_diastolic = models.PositiveIntegerField(null=True, blank=True)
    heart_rate = models.PositiveIntegerField(null=True, blank=True, help_text="Beats per minute")
    respiratory_rate = models.PositiveIntegerField(null=True, blank=True, help_text="Breaths per minute")
    oxygen_saturation = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="SpO2 percentage"
    )
    
    # Physical measurements
    height = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Height in cm"
    )
    weight = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Weight in kg"
    )
    bmi = models.DecimalField(
        max_digits=4, 
        decimal_places=2, 
        null=True, 
        blank=True,
        editable=False
    )
    
    # Additional measurements
    blood_glucose = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Blood glucose level"
    )
    pain_scale = models.PositiveIntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="Pain scale 0-10"
    )
    
    notes = models.TextField(blank=True, null=True, help_text="Additional notes about vitals")
    
    class Meta:
        db_table = 'patient_vitals'
        ordering = ['-recorded_date']
    
    def __str__(self):
        return f"{self.patient.full_name} - Vitals ({self.recorded_date.strftime('%Y-%m-%d %H:%M')})"
    
    def save(self, *args, **kwargs):
        # Calculate BMI if height and weight are provided
        if self.height and self.weight:
            height_m = float(self.height) / 100  # Convert cm to meters
            self.bmi = float(self.weight) / (height_m ** 2)
        
        super().save(*args, **kwargs)

class PatientAllergy(models.Model):
    """
    Patient allergies with detailed information
    """
    SEVERITY_CHOICES = [
        ('mild', 'Mild'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
        ('life_threatening', 'Life Threatening'),
    ]
    
    ALLERGY_TYPES = [
        ('drug', 'Drug/Medication'),
        ('food', 'Food'),
        ('environmental', 'Environmental'),
        ('contact', 'Contact'),
        ('other', 'Other'),
    ]
    
    # FIXED: Changed related_name to avoid conflict
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='allergy_details')
    allergy_type = models.CharField(max_length=20, choices=ALLERGY_TYPES)
    allergen = models.CharField(max_length=200, help_text="Name of the allergen")
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    symptoms = models.TextField(help_text="Allergic reaction symptoms")
    treatment = models.TextField(blank=True, null=True, help_text="Treatment for allergic reaction")
    onset_date = models.DateField(null=True, blank=True, help_text="When allergy was first discovered")
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'patient_allergies'
        unique_together = ['patient', 'allergen']
        ordering = ['-severity', 'allergen']
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.allergen} ({self.severity})"

class PatientMedication(models.Model):
    """
    Current medications for patients
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('discontinued', 'Discontinued'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
    ]
    
    # FIXED: Changed related_name to avoid conflict
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medication_list')
    medication_name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100, help_text="e.g., 500mg, 2 tablets")
    frequency = models.CharField(max_length=100, help_text="e.g., Twice daily, Every 8 hours")
    route = models.CharField(max_length=50, help_text="e.g., Oral, IV, IM")
    
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    prescribed_by = models.CharField(max_length=200, help_text="Prescribing doctor")
    purpose = models.CharField(max_length=200, help_text="Purpose/condition for medication")
    instructions = models.TextField(blank=True, null=True, help_text="Special instructions")
    side_effects = models.TextField(blank=True, null=True, help_text="Observed side effects")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'patient_medications'
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.medication_name}"

class PatientNote(models.Model):
    """
    Clinical notes and observations about patients
    """
    NOTE_TYPES = [
        ('general', 'General Note'),
        ('clinical', 'Clinical Note'),
        ('nursing', 'Nursing Note'),
        ('progress', 'Progress Note'),
        ('discharge', 'Discharge Note'),
        ('follow_up', 'Follow-up Note'),
    ]
    
    # FIXED: Changed related_name to avoid conflict
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='clinical_notes')
    note_type = models.CharField(max_length=20, choices=NOTE_TYPES, default='general')
    title = models.CharField(max_length=200)
    content = models.TextField()
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    is_confidential = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'patient_notes'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.title}"