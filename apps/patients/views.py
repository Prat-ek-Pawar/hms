# apps/patients/views.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg
from django.shortcuts import get_object_or_404
from django.utils import timezone
from apps.permissions.mixins import DRFPermissionMixin, HasPermissionMixin
from .models import (
    Patient, PatientInsurance, PatientDocument, PatientVitals,
    PatientAllergy, PatientMedication, PatientNote
)
from .serializers import (
    PatientListSerializer, PatientDetailSerializer, PatientCreateUpdateSerializer,
    PatientInsuranceSerializer, PatientDocumentSerializer, PatientVitalsSerializer,
    PatientAllergySerializer, PatientMedicationSerializer, PatientNoteSerializer
)

class PatientViewSet(DRFPermissionMixin, viewsets.ModelViewSet):
    queryset = Patient.objects.select_related('user', 'created_by').prefetch_related(
        'insurance_policies', 'documents', 'vitals', 'allergy_details', 
        'current_medications', 'notes'
    )
    module_name = 'patients'  # Uses patients.create, patients.read, etc.
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'status', 'gender', 'blood_group', 'patient_type', 'city', 'state', 
        'marital_status', 'registration_date'
    ]
    search_fields = [
        'first_name', 'last_name', 'patient_id', 'mobile_primary', 
        'email', 'emergency_contact_name'
    ]
    ordering_fields = [
        'first_name', 'last_name', 'age', 'registration_date', 
        'last_visit_date', 'total_visits'
    ]
    ordering = ['-registration_date']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PatientListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return PatientCreateUpdateSerializer
        return PatientDetailSerializer
    
    def get_queryset(self):
        queryset = Patient.objects.select_related('user', 'created_by').prefetch_related(
            'insurance_policies', 'documents', 'vitals', 'allergy_details', 
            'current_medications', 'notes'
        )
        
        # Filter by age range
        min_age = self.request.query_params.get('min_age')
        max_age = self.request.query_params.get('max_age')
        if min_age:
            queryset = queryset.filter(age__gte=min_age)
        if max_age:
            queryset = queryset.filter(age__lte=max_age)
        
        # Filter by registration date range
        from_date = self.request.query_params.get('from_date')
        to_date = self.request.query_params.get('to_date')
        if from_date:
            queryset = queryset.filter(registration_date__gte=from_date)
        if to_date:
            queryset = queryset.filter(registration_date__lte=to_date)
        
        # Filter by insurance status
        has_insurance = self.request.query_params.get('has_insurance')
        if has_insurance is not None:
            if has_insurance.lower() == 'true':
                queryset = queryset.filter(insurance_policies__isnull=False).distinct()
            else:
                queryset = queryset.filter(insurance_policies__isnull=True)
        
        # Filter by chronic conditions
        has_chronic_conditions = self.request.query_params.get('has_chronic_conditions')
        if has_chronic_conditions is not None:
            if has_chronic_conditions.lower() == 'true':
                queryset = queryset.exclude(chronic_conditions__isnull=True).exclude(chronic_conditions='')
            else:
                queryset = queryset.filter(Q(chronic_conditions__isnull=True) | Q(chronic_conditions=''))
        
        return queryset.distinct()
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def insurance(self, request, pk=None):
        """Get patient's insurance policies"""
        patient = self.get_object()
        insurance_policies = patient.insurance_policies.all()
        serializer = PatientInsuranceSerializer(insurance_policies, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_insurance(self, request, pk=None):
        """Add insurance policy to patient"""
        patient = self.get_object()
        data = request.data.copy()
        data['patient'] = patient.id
        
        serializer = PatientInsuranceSerializer(data=data)
        if serializer.is_valid():
            serializer.save(patient=patient)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def documents(self, request, pk=None):
        """Get patient's documents"""
        patient = self.get_object()
        documents = patient.documents.all()
        
        # Filter by document type
        doc_type = request.query_params.get('type')
        if doc_type:
            documents = documents.filter(document_type=doc_type)
        
        # Apply pagination
        page = self.paginate_queryset(documents)
        if page is not None:
            serializer = PatientDocumentSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = PatientDocumentSerializer(documents, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def upload_document(self, request, pk=None):
        """Upload document for patient"""
        patient = self.get_object()
        data = request.data.copy()
        data['patient'] = patient.id
        
        serializer = PatientDocumentSerializer(data=data)
        if serializer.is_valid():
            serializer.save(patient=patient, uploaded_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def vitals(self, request, pk=None):
        """Get patient's vital signs history"""
        patient = self.get_object()
        vitals = patient.vitals.all()
        
        # Filter by date range
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        if from_date:
            vitals = vitals.filter(recorded_date__gte=from_date)
        if to_date:
            vitals = vitals.filter(recorded_date__lte=to_date)
        
        # Apply pagination
        page = self.paginate_queryset(vitals)
        if page is not None:
            serializer = PatientVitalsSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = PatientVitalsSerializer(vitals, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def record_vitals(self, request, pk=None):
        """Record vital signs for patient"""
        patient = self.get_object()
        data = request.data.copy()
        data['patient'] = patient.id
        
        serializer = PatientVitalsSerializer(data=data)
        if serializer.is_valid():
            serializer.save(patient=patient, recorded_by=request.user)
            
            # Update patient's height and weight if provided
            if 'height' in data and data['height']:
                patient.height = data['height']
            if 'weight' in data and data['weight']:
                patient.weight = data['weight']
            patient.save()
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def allergies(self, request, pk=None):
        """Get patient's allergies"""
        patient = self.get_object()
        allergies = patient.allergy_details.filter(is_active=True)
        serializer = PatientAllergySerializer(allergies, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_allergy(self, request, pk=None):
        """Add allergy to patient"""
        patient = self.get_object()
        data = request.data.copy()
        data['patient'] = patient.id
        
        serializer = PatientAllergySerializer(data=data)
        if serializer.is_valid():
            serializer.save(patient=patient)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def medications(self, request, pk=None):
        """Get patient's current medications"""
        patient = self.get_object()
        medications = patient.current_medications.filter(status='active')
        serializer = PatientMedicationSerializer(medications, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_medication(self, request, pk=None):
        """Add medication to patient"""
        patient = self.get_object()
        data = request.data.copy()
        data['patient'] = patient.id
        
        serializer = PatientMedicationSerializer(data=data)
        if serializer.is_valid():
            serializer.save(patient=patient)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def notes(self, request, pk=None):
        """Get patient's clinical notes"""
        patient = self.get_object()
        notes = patient.notes.all()
        
        # Filter by note type
        note_type = request.query_params.get('type')
        if note_type:
            notes = notes.filter(note_type=note_type)
        
        # Apply pagination
        page = self.paginate_queryset(notes)
        if page is not None:
            serializer = PatientNoteSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = PatientNoteSerializer(notes, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_note(self, request, pk=None):
        """Add clinical note for patient"""
        patient = self.get_object()
        data = request.data.copy()
        data['patient'] = patient.id
        
        serializer = PatientNoteSerializer(data=data)
        if serializer.is_valid():
            serializer.save(patient=patient, created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def update_visit(self, request, pk=None):
        """Update patient's last visit and increment visit count"""
        patient = self.get_object()
        patient.last_visit_date = timezone.now()
        patient.total_visits += 1
        patient.save(update_fields=['last_visit_date', 'total_visits'])
        
        return Response({
            'message': 'Visit updated successfully',
            'last_visit_date': patient.last_visit_date,
            'total_visits': patient.total_visits
        })
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Advanced search for patients"""
        query = request.query_params.get('q', '')
        blood_group = request.query_params.get('blood_group')
        location = request.query_params.get('location')
        
        queryset = self.get_queryset()
        
        if query:
            queryset = queryset.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(patient_id__icontains=query) |
                Q(mobile_primary__icontains=query) |
                Q(email__icontains=query)
            )
        
        if blood_group:
            queryset = queryset.filter(blood_group=blood_group)
        
        if location:
            queryset = queryset.filter(
                Q(city__icontains=location) |
                Q(state__icontains=location)
            )
        
        # Apply pagination
        page = self.paginate_queryset(queryset.distinct())
        if page is not None:
            serializer = PatientListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = PatientListSerializer(queryset.distinct(), many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get patient statistics"""
        # Check permission for statistics
        from apps.permissions.models import UserPermission
        if not UserPermission.has_permission(request.user, 'patients.read'):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        total_patients = Patient.objects.count()
        active_patients = Patient.objects.filter(status='active').count()
        
        # Gender distribution
        gender_stats = Patient.objects.values('gender').annotate(count=Count('id'))
        
        # Age groups
        age_groups = {
            'children': Patient.objects.filter(age__lt=18).count(),
            'adults': Patient.objects.filter(age__gte=18, age__lt=65).count(),
            'elderly': Patient.objects.filter(age__gte=65).count(),
        }
        
        # Blood group distribution
        blood_group_stats = Patient.objects.exclude(
            blood_group__isnull=True
        ).values('blood_group').annotate(count=Count('id'))
        
        # Recent registrations (last 30 days)
        from datetime import timedelta
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_registrations = Patient.objects.filter(
            registration_date__gte=thirty_days_ago
        ).count()
        
        return Response({
            'total_patients': total_patients,
            'active_patients': active_patients,
            'inactive_patients': total_patients - active_patients,
            'recent_registrations': recent_registrations,
            'gender_distribution': list(gender_stats),
            'age_groups': age_groups,
            'blood_group_distribution': list(blood_group_stats),
        })
    
    @action(detail=False, methods=['get'])
    def emergency_contacts(self, request):
        """Get emergency contact information for all patients"""
        # This might be used for emergency situations
        patients = Patient.objects.filter(status='active').values(
            'patient_id', 'first_name', 'last_name',
            'emergency_contact_name', 'emergency_contact_phone',
            'emergency_contact_relation'
        )
        return Response(list(patients))

class PatientInsuranceViewSet(DRFPermissionMixin, viewsets.ModelViewSet):
    queryset = PatientInsurance.objects.select_related('patient')
    serializer_class = PatientInsuranceSerializer
    module_name = 'patients'
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['patient', 'status', 'policy_type']
    ordering = ['-start_date']

class PatientDocumentViewSet(DRFPermissionMixin, viewsets.ModelViewSet):
    queryset = PatientDocument.objects.select_related('patient', 'uploaded_by')
    serializer_class = PatientDocumentSerializer
    module_name = 'patients'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['patient', 'document_type', 'is_sensitive']
    search_fields = ['title', 'description']
    ordering = ['-document_date']
    
    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)

class PatientVitalsViewSet(DRFPermissionMixin, viewsets.ModelViewSet):
    queryset = PatientVitals.objects.select_related('patient', 'recorded_by')
    serializer_class = PatientVitalsSerializer
    module_name = 'patients'
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['patient']
    ordering = ['-recorded_date']
    
    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user)

class PatientAllergyViewSet(DRFPermissionMixin, viewsets.ModelViewSet):
    queryset = PatientAllergy.objects.select_related('patient')
    serializer_class = PatientAllergySerializer
    module_name = 'patients'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['patient', 'allergy_type', 'severity', 'is_active']
    search_fields = ['allergen', 'symptoms']
    ordering = ['-severity', 'allergen']

class PatientMedicationViewSet(DRFPermissionMixin, viewsets.ModelViewSet):
    queryset = PatientMedication.objects.select_related('patient')
    serializer_class = PatientMedicationSerializer
    module_name = 'patients'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['patient', 'status']
    search_fields = ['medication_name', 'prescribed_by']
    ordering = ['-start_date']

class PatientNoteViewSet(DRFPermissionMixin, viewsets.ModelViewSet):
    queryset = PatientNote.objects.select_related('patient', 'created_by')
    serializer_class = PatientNoteSerializer
    module_name = 'patients'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['patient', 'note_type', 'is_confidential']
    search_fields = ['title', 'content']
    ordering = ['-created_at']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)