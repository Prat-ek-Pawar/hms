from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.users.serializers import UserSerializer
from .models import (
    Patient, PatientInsurance, PatientDocument, PatientVitals,
    PatientAllergy, PatientMedication, PatientNote
)

User = get_user_model()

class PatientInsuranceSerializer(serializers.ModelSerializer):
    is_valid = serializers.ReadOnlyField()
    
    class Meta:
        model = PatientInsurance
        fields = [
            'id', 'provider_name', 'policy_number', 'policy_type',
            'coverage_amount', 'premium_amount', 'start_date', 'expiry_date',
            'status', 'covered_treatments', 'excluded_treatments',
            'policy_document', 'is_valid', 'created_at', 'updated_at'
        ]

class PatientDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    
    class Meta:
        model = PatientDocument
        fields = [
            'id', 'document_type', 'title', 'description', 'document_file',
            'document_date', 'uploaded_by', 'uploaded_by_name', 'is_sensitive', 'created_at'
        ]
        extra_kwargs = {
            'uploaded_by': {'write_only': True}
        }

class PatientVitalsSerializer(serializers.ModelSerializer):
    recorded_by_name = serializers.CharField(source='recorded_by.get_full_name', read_only=True)
    
    class Meta:
        model = PatientVitals
        fields = [
            'id', 'temperature', 'blood_pressure_systolic', 'blood_pressure_diastolic',
            'heart_rate', 'respiratory_rate', 'oxygen_saturation', 'height',
            'weight', 'bmi', 'blood_glucose', 'pain_scale', 'notes',
            'recorded_by', 'recorded_by_name', 'recorded_date'
        ]
        extra_kwargs = {
            'recorded_by': {'write_only': True}
        }

class PatientAllergySerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientAllergy
        fields = [
            'id', 'allergy_type', 'allergen', 'severity', 'symptoms',
            'treatment', 'onset_date', 'is_active', 'notes',
            'created_at', 'updated_at'
        ]

class PatientMedicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientMedication
        fields = [
            'id', 'medication_name', 'dosage', 'frequency', 'route',
            'start_date', 'end_date', 'status', 'prescribed_by',
            'purpose', 'instructions', 'side_effects',
            'created_at', 'updated_at'
        ]

class PatientNoteSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = PatientNote
        fields = [
            'id', 'note_type', 'title', 'content', 'created_by',
            'created_by_name', 'is_confidential', 'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'created_by': {'write_only': True}
        }

class PatientListSerializer(serializers.ModelSerializer):
    """Serializer for patient list view with basic information"""
    full_name = serializers.CharField(read_only=True)
    full_address = serializers.CharField(read_only=True)
    is_insurance_valid = serializers.ReadOnlyField()
    
    class Meta:
        model = Patient
        fields = [
            'id', 'patient_id', 'full_name', 'gender', 'age',
            'mobile_primary', 'email', 'city', 'state',
            'blood_group', 'patient_type', 'status',
            'registration_date', 'last_visit_date', 'total_visits',
            'is_insurance_valid', 'full_address'
        ]

class PatientDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for patient with all related information"""
    user = UserSerializer(read_only=True)
    insurance_policies = PatientInsuranceSerializer(many=True, read_only=True)
    documents = PatientDocumentSerializer(many=True, read_only=True)
    recent_vitals = PatientVitalsSerializer(source='vitals', many=True, read_only=True)
    allergy_details = PatientAllergySerializer(many=True, read_only=True)
    current_medications = PatientMedicationSerializer(many=True, read_only=True)
    recent_notes = PatientNoteSerializer(source='notes', many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    # Computed fields
    full_name = serializers.CharField(read_only=True)
    full_address = serializers.CharField(read_only=True)
    is_insurance_valid = serializers.ReadOnlyField()
    
    class Meta:
        model = Patient
        fields = '__all__'

class PatientCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating patients"""
    user_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = Patient
        exclude = ['patient_id', 'age', 'bmi', 'total_visits']
    
    def validate_user_id(self, value):
        if value:
            try:
                user = User.objects.get(id=value)
                if hasattr(user, 'patient_profile'):
                    raise serializers.ValidationError("User already has a patient profile")
                return value
            except User.DoesNotExist:
                raise serializers.ValidationError("User not found")
        return value
    
    def validate_mobile_primary(self, value):
        if self.instance:
            # For updates, exclude current instance
            existing = Patient.objects.filter(
                mobile_primary=value
            ).exclude(id=self.instance.id)
        else:
            existing = Patient.objects.filter(mobile_primary=value)
        
        if existing.exists():
            raise serializers.ValidationError("Patient with this mobile number already exists")
        return value
    
    def create(self, validated_data):
        user_id = validated_data.pop('user_id', None)
        
        if user_id:
            user = User.objects.get(id=user_id)
            validated_data['user'] = user
        
        patient = Patient.objects.create(**validated_data)
        return patient
    
    def update(self, instance, validated_data):
        user_id = validated_data.pop('user_id', None)
        
        if user_id:
            user = User.objects.get(id=user_id)
            instance.user = user
        
        # Update basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        return instance