# apps/doctors/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.users.serializers import UserSerializer
from .models import (
    Doctor, Specialty, Qualification, Hospital, DoctorSpecialty,
    DoctorQualification, DoctorExperience, DoctorAvailability, DoctorReview
)

User = get_user_model()

class SpecialtySerializer(serializers.ModelSerializer):
    doctors_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Specialty
        fields = [
            'id', 'name', 'code', 'description', 'department',
            'is_active', 'doctors_count', 'created_at', 'updated_at'
        ]
    
    def get_doctors_count(self, obj):
        return obj.doctors.filter(status='active').count()

class QualificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Qualification
        fields = [
            'id', 'degree_name', 'degree_type', 'short_name',
            'description', 'duration_years', 'is_active', 'created_at'
        ]

class HospitalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hospital
        fields = [
            'id', 'name', 'address', 'city', 'state', 'country',
            'pincode', 'phone', 'email', 'website', 'hospital_type',
            'bed_capacity', 'is_active', 'created_at'
        ]

class DoctorSpecialtySerializer(serializers.ModelSerializer):
    specialty_name = serializers.CharField(source='specialty.name', read_only=True)
    specialty_code = serializers.CharField(source='specialty.code', read_only=True)
    
    class Meta:
        model = DoctorSpecialty
        fields = [
            'id', 'specialty', 'specialty_name', 'specialty_code',
            'is_primary', 'years_of_experience', 'board_certified',
            'certification_date', 'created_at'
        ]

class DoctorQualificationSerializer(serializers.ModelSerializer):
    qualification_name = serializers.CharField(source='qualification.degree_name', read_only=True)
    qualification_short_name = serializers.CharField(source='qualification.short_name', read_only=True)
    qualification_type = serializers.CharField(source='qualification.degree_type', read_only=True)
    verified_by_name = serializers.CharField(source='verified_by.get_full_name', read_only=True)
    
    class Meta:
        model = DoctorQualification
        fields = [
            'id', 'qualification', 'qualification_name', 'qualification_short_name',
            'qualification_type', 'institution_name', 'university_name',
            'year_started', 'year_completed', 'grade_percentage',
            'certificate_file', 'is_verified', 'verified_by', 'verified_by_name',
            'verified_at', 'created_at'
        ]

class DoctorExperienceSerializer(serializers.ModelSerializer):
    hospital_name = serializers.CharField(source='hospital.name', read_only=True)
    hospital_city = serializers.CharField(source='hospital.city', read_only=True)
    duration_months = serializers.ReadOnlyField()
    
    class Meta:
        model = DoctorExperience
        fields = [
            'id', 'hospital', 'hospital_name', 'hospital_city',
            'position', 'department', 'start_date', 'end_date',
            'is_current', 'responsibilities', 'achievements',
            'duration_months', 'created_at'
        ]

class DoctorAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorAvailability
        fields = [
            'id', 'day_of_week', 'start_time', 'end_time',
            'is_available', 'consultation_type', 'max_patients',
            'created_at', 'updated_at'
        ]

class DoctorReviewSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    
    class Meta:
        model = DoctorReview
        fields = [
            'id', 'rating', 'review_text', 'consultation_date',
            'patient_name', 'is_verified', 'is_anonymous',
            'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'patient': {'write_only': True}
        }
    
    def get_patient_name(self, obj):
        return "Anonymous" if obj.is_anonymous else obj.patient.get_full_name()

class DoctorListSerializer(serializers.ModelSerializer):
    """Serializer for doctor list view with basic information"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    primary_specialty = serializers.CharField(read_only=True)
    all_specialties = serializers.CharField(read_only=True)
    highest_qualification = serializers.SerializerMethodField()
    is_license_valid = serializers.ReadOnlyField()
    
    class Meta:
        model = Doctor
        fields = [
            'id', 'user_name', 'user_email', 'gender', 'age',
            'mobile_primary', 'email_primary', 'city', 'state',
            'medical_license_number', 'years_of_experience',
            'primary_specialty', 'all_specialties', 'highest_qualification',
            'consultation_fee', 'consultation_type', 'average_rating',
            'total_reviews', 'status', 'is_license_valid',
            'is_available_online', 'is_available_offline'
        ]
    
    def get_highest_qualification(self, obj):
        qual = obj.highest_qualification
        return qual.short_name if qual else None

class DoctorDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for doctor with all related information"""
    user = UserSerializer(read_only=True)
    specialties_detail = DoctorSpecialtySerializer(source='doctorspecialty_set', many=True, read_only=True)
    qualifications_detail = DoctorQualificationSerializer(source='doctorqualification_set', many=True, read_only=True)
    experiences = DoctorExperienceSerializer(many=True, read_only=True)
    availability = DoctorAvailabilitySerializer(many=True, read_only=True)
    recent_reviews = DoctorReviewSerializer(source='reviews', many=True, read_only=True)
    
    # Computed fields
    primary_specialty = serializers.CharField(read_only=True)
    all_specialties = serializers.CharField(read_only=True)
    highest_qualification = serializers.SerializerMethodField()
    is_license_valid = serializers.ReadOnlyField()
    
    class Meta:
        model = Doctor
        fields = '__all__'
    
    def get_highest_qualification(self, obj):
        qual = obj.highest_qualification
        return {
            'id': qual.id,
            'short_name': qual.short_name,
            'degree_name': qual.degree_name
        } if qual else None

class DoctorCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating doctors"""
    user_id = serializers.IntegerField(write_only=True)
    specialties = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    qualifications = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Doctor
        exclude = ['user', 'age', 'average_rating', 'total_reviews', 'total_consultations']
    
    def validate_user_id(self, value):
        try:
            user = User.objects.get(id=value)
            if hasattr(user, 'doctor_profile'):
                raise serializers.ValidationError("User already has a doctor profile")
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")
    
    def validate_medical_license_number(self, value):
        if self.instance:
            # For updates, exclude current instance
            existing = Doctor.objects.filter(
                medical_license_number=value
            ).exclude(id=self.instance.id)
        else:
            existing = Doctor.objects.filter(medical_license_number=value)
        
        if existing.exists():
            raise serializers.ValidationError("Medical license number already exists")
        return value
    
    def create(self, validated_data):
        user_id = validated_data.pop('user_id')
        specialties_data = validated_data.pop('specialties', [])
        qualifications_data = validated_data.pop('qualifications', [])
        
        user = User.objects.get(id=user_id)
        validated_data['user'] = user
        
        doctor = Doctor.objects.create(**validated_data)
        
        # Add specialties
        for specialty_id in specialties_data:
            try:
                specialty = Specialty.objects.get(id=specialty_id)
                DoctorSpecialty.objects.create(
                    doctor=doctor,
                    specialty=specialty,
                    is_primary=(len(doctor.doctorspecialty_set.all()) == 0)
                )
            except Specialty.DoesNotExist:
                continue
        
        # Add qualifications
        for qual_data in qualifications_data:
            try:
                qualification = Qualification.objects.get(id=qual_data['qualification_id'])
                DoctorQualification.objects.create(
                    doctor=doctor,
                    qualification=qualification,
                    institution_name=qual_data.get('institution_name', ''),
                    university_name=qual_data.get('university_name', ''),
                    year_started=qual_data.get('year_started'),
                    year_completed=qual_data.get('year_completed'),
                    grade_percentage=qual_data.get('grade_percentage')
                )
            except (Qualification.DoesNotExist, KeyError):
                continue
        
        return doctor
    
    def update(self, instance, validated_data):
        specialties_data = validated_data.pop('specialties', None)
        qualifications_data = validated_data.pop('qualifications', None)
        
        # Update basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update specialties if provided
        if specialties_data is not None:
            instance.doctorspecialty_set.all().delete()
            for i, specialty_id in enumerate(specialties_data):
                try:
                    specialty = Specialty.objects.get(id=specialty_id)
                    DoctorSpecialty.objects.create(
                        doctor=instance,
                        specialty=specialty,
                        is_primary=(i == 0)
                    )
                except Specialty.DoesNotExist:
                    continue
        
        return instance