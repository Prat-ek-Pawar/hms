# apps/doctors/views.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Avg, Count
from django.shortcuts import get_object_or_404
from apps.permissions.mixins import DRFPermissionMixin, HasPermissionMixin
from .models import (
    Doctor, Specialty, Qualification, Hospital, DoctorSpecialty,
    DoctorQualification, DoctorExperience, DoctorAvailability, DoctorReview
)
from .serializers import (
    DoctorListSerializer, DoctorDetailSerializer, DoctorCreateUpdateSerializer,
    SpecialtySerializer, QualificationSerializer, HospitalSerializer,
    DoctorSpecialtySerializer, DoctorQualificationSerializer,
    DoctorExperienceSerializer, DoctorAvailabilitySerializer, DoctorReviewSerializer
)

class SpecialtyViewSet(DRFPermissionMixin, viewsets.ModelViewSet):
    queryset = Specialty.objects.all()
    serializer_class = SpecialtySerializer
    module_name = 'doctors'  # Uses doctors.create, doctors.read, etc.
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'department']
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        queryset = Specialty.objects.all()
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def doctors(self, request, pk=None):
        """Get all doctors for this specialty"""
        specialty = self.get_object()
        doctors = Doctor.objects.filter(
            specialties=specialty,
            status='active'
        ).select_related('user')
        
        serializer = DoctorListSerializer(doctors, many=True)
        return Response(serializer.data)

class QualificationViewSet(DRFPermissionMixin, viewsets.ModelViewSet):
    queryset = Qualification.objects.all()
    serializer_class = QualificationSerializer
    module_name = 'doctors'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['degree_type', 'is_active']
    search_fields = ['degree_name', 'short_name']
    ordering_fields = ['degree_name', 'created_at']
    ordering = ['degree_type', 'degree_name']

class HospitalViewSet(DRFPermissionMixin, viewsets.ModelViewSet):
    queryset = Hospital.objects.all()
    serializer_class = HospitalSerializer
    module_name = 'doctors'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['hospital_type', 'city', 'state', 'is_active']
    search_fields = ['name', 'city', 'state']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

class DoctorViewSet(DRFPermissionMixin, viewsets.ModelViewSet):
    queryset = Doctor.objects.select_related('user').prefetch_related(
        'specialties', 'qualifications', 'experiences', 'availability'
    )
    module_name = 'doctors'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'status', 'gender', 'city', 'state', 'consultation_type',
        'is_available_online', 'is_available_offline'
    ]
    search_fields = [
        'user__first_name', 'user__last_name', 'user__email',
        'medical_license_number', 'mobile_primary'
    ]
    ordering_fields = [
        'user__first_name', 'years_of_experience', 'consultation_fee',
        'average_rating', 'created_at'
    ]
    ordering = ['user__first_name']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return DoctorListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return DoctorCreateUpdateSerializer
        return DoctorDetailSerializer
    
    def get_queryset(self):
        queryset = Doctor.objects.select_related('user').prefetch_related(
            'specialties', 'qualifications', 'experiences', 'availability'
        )
        
        # Filter by specialty
        specialty_id = self.request.query_params.get('specialty')
        if specialty_id:
            queryset = queryset.filter(specialties__id=specialty_id)
        
        # Filter by experience range
        min_experience = self.request.query_params.get('min_experience')
        max_experience = self.request.query_params.get('max_experience')
        if min_experience:
            queryset = queryset.filter(years_of_experience__gte=min_experience)
        if max_experience:
            queryset = queryset.filter(years_of_experience__lte=max_experience)
        
        # Filter by consultation fee range
        min_fee = self.request.query_params.get('min_fee')
        max_fee = self.request.query_params.get('max_fee')
        if min_fee:
            queryset = queryset.filter(consultation_fee__gte=min_fee)
        if max_fee:
            queryset = queryset.filter(consultation_fee__lte=max_fee)
        
        # Filter by rating
        min_rating = self.request.query_params.get('min_rating')
        if min_rating:
            queryset = queryset.filter(average_rating__gte=min_rating)
        
        # Filter by availability
        available_online = self.request.query_params.get('available_online')
        if available_online is not None:
            queryset = queryset.filter(is_available_online=available_online.lower() == 'true')
        
        return queryset.distinct()
    
    @action(detail=True, methods=['get'])
    def specialties(self, request, pk=None):
        """Get doctor's specialties with details"""
        doctor = self.get_object()
        specialties = doctor.doctorspecialty_set.select_related('specialty').all()
        serializer = DoctorSpecialtySerializer(specialties, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_specialty(self, request, pk=None):
        """Add specialty to doctor"""
        doctor = self.get_object()
        specialty_id = request.data.get('specialty_id')
        is_primary = request.data.get('is_primary', False)
        years_of_experience = request.data.get('years_of_experience', 0)
        
        if not specialty_id:
            return Response(
                {'error': 'specialty_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            specialty = Specialty.objects.get(id=specialty_id)
        except Specialty.DoesNotExist:
            return Response(
                {'error': 'Specialty not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if already exists
        if DoctorSpecialty.objects.filter(doctor=doctor, specialty=specialty).exists():
            return Response(
                {'error': 'Doctor already has this specialty'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # If setting as primary, unset other primary specialties
        if is_primary:
            DoctorSpecialty.objects.filter(doctor=doctor, is_primary=True).update(is_primary=False)
        
        doctor_specialty = DoctorSpecialty.objects.create(
            doctor=doctor,
            specialty=specialty,
            is_primary=is_primary,
            years_of_experience=years_of_experience
        )
        
        serializer = DoctorSpecialtySerializer(doctor_specialty)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['delete'])
    def remove_specialty(self, request, pk=None):
        """Remove specialty from doctor"""
        doctor = self.get_object()
        specialty_id = request.data.get('specialty_id')
        
        if not specialty_id:
            return Response(
                {'error': 'specialty_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            doctor_specialty = DoctorSpecialty.objects.get(
                doctor=doctor, 
                specialty_id=specialty_id
            )
            doctor_specialty.delete()
            return Response({'message': 'Specialty removed successfully'})
        except DoctorSpecialty.DoesNotExist:
            return Response(
                {'error': 'Doctor does not have this specialty'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def qualifications(self, request, pk=None):
        """Get doctor's qualifications"""
        doctor = self.get_object()
        qualifications = doctor.doctorqualification_set.select_related('qualification').all()
        serializer = DoctorQualificationSerializer(qualifications, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_qualification(self, request, pk=None):
        """Add qualification to doctor"""
        doctor = self.get_object()
        data = request.data.copy()
        data['doctor'] = doctor.id
        
        serializer = DoctorQualificationSerializer(data=data)
        if serializer.is_valid():
            serializer.save(doctor=doctor)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def experiences(self, request, pk=None):
        """Get doctor's work experiences"""
        doctor = self.get_object()
        experiences = doctor.experiences.select_related('hospital').all()
        serializer = DoctorExperienceSerializer(experiences, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_experience(self, request, pk=None):
        """Add work experience to doctor"""
        doctor = self.get_object()
        data = request.data.copy()
        data['doctor'] = doctor.id
        
        serializer = DoctorExperienceSerializer(data=data)
        if serializer.is_valid():
            serializer.save(doctor=doctor)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def availability(self, request, pk=None):
        """Get doctor's availability schedule"""
        doctor = self.get_object()
        availability = doctor.availability.all()
        serializer = DoctorAvailabilitySerializer(availability, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def set_availability(self, request, pk=None):
        """Set doctor's availability for a day"""
        doctor = self.get_object()
        data = request.data.copy()
        data['doctor'] = doctor.id
        
        # Check if availability already exists for this day
        day_of_week = data.get('day_of_week')
        start_time = data.get('start_time')
        
        existing = DoctorAvailability.objects.filter(
            doctor=doctor,
            day_of_week=day_of_week,
            start_time=start_time
        ).first()
        
        if existing:
            serializer = DoctorAvailabilitySerializer(existing, data=data, partial=True)
        else:
            serializer = DoctorAvailabilitySerializer(data=data)
        
        if serializer.is_valid():
            serializer.save(doctor=doctor)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        """Get doctor's reviews and ratings"""
        doctor = self.get_object()
        reviews = doctor.reviews.select_related('patient').all()
        
        # Pagination
        page = self.paginate_queryset(reviews)
        if page is not None:
            serializer = DoctorReviewSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = DoctorReviewSerializer(reviews, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_review(self, request, pk=None):
        """Add review for doctor"""
        doctor = self.get_object()
        data = request.data.copy()
        data['doctor'] = doctor.id
        data['patient'] = request.user.id
        
        serializer = DoctorReviewSerializer(data=data)
        if serializer.is_valid():
            review = serializer.save(doctor=doctor, patient=request.user)
            
            # Update doctor's average rating
            avg_rating = doctor.reviews.aggregate(avg=Avg('rating'))['avg']
            doctor.average_rating = round(avg_rating, 2) if avg_rating else 0
            doctor.total_reviews = doctor.reviews.count()
            doctor.save(update_fields=['average_rating', 'total_reviews'])
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Advanced search for doctors"""
        query = request.query_params.get('q', '')
        specialty = request.query_params.get('specialty')
        location = request.query_params.get('location')
        
        queryset = self.get_queryset()
        
        if query:
            queryset = queryset.filter(
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query) |
                Q(specialties__name__icontains=query) |
                Q(qualifications__degree_name__icontains=query)
            )
        
        if specialty:
            queryset = queryset.filter(specialties__name__icontains=specialty)
        
        if location:
            queryset = queryset.filter(
                Q(city__icontains=location) |
                Q(state__icontains=location)
            )
        
        # Apply pagination
        page = self.paginate_queryset(queryset.distinct())
        if page is not None:
            serializer = DoctorListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = DoctorListSerializer(queryset.distinct(), many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get doctor statistics"""
        # Check permission for statistics
        from apps.permissions.models import UserPermission
        if not UserPermission.has_permission(request.user, 'doctors.read'):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        total_doctors = Doctor.objects.count()
        active_doctors = Doctor.objects.filter(status='active').count()
        specialties_count = Specialty.objects.filter(is_active=True).count()
        
        # Top specialties
        top_specialties = Specialty.objects.annotate(
            doctor_count=Count('doctors')
        ).order_by('-doctor_count')[:5]
        
        # Average ratings
        avg_rating = Doctor.objects.aggregate(avg=Avg('average_rating'))['avg']
        
        return Response({
            'total_doctors': total_doctors,
            'active_doctors': active_doctors,
            'inactive_doctors': total_doctors - active_doctors,
            'specialties_count': specialties_count,
            'average_rating': round(avg_rating, 2) if avg_rating else 0,
            'top_specialties': [
                {
                    'name': s.name,
                    'doctor_count': s.doctor_count
                } for s in top_specialties
            ]
        })

class DoctorExperienceViewSet(DRFPermissionMixin, viewsets.ModelViewSet):
    queryset = DoctorExperience.objects.select_related('doctor', 'hospital')
    serializer_class = DoctorExperienceSerializer
    module_name = 'doctors'
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['doctor', 'hospital', 'position', 'is_current']
    ordering = ['-start_date']

class DoctorAvailabilityViewSet(DRFPermissionMixin, viewsets.ModelViewSet):
    queryset = DoctorAvailability.objects.select_related('doctor')
    serializer_class = DoctorAvailabilitySerializer
    module_name = 'doctors'
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['doctor', 'day_of_week', 'is_available', 'consultation_type']
    ordering = ['day_of_week', 'start_time']

class DoctorReviewViewSet(DRFPermissionMixin, viewsets.ModelViewSet):
    queryset = DoctorReview.objects.select_related('doctor', 'patient')
    serializer_class = DoctorReviewSerializer
    module_name = 'doctors'
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['doctor', 'rating', 'is_verified']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = DoctorReview.objects.select_related('doctor', 'patient')
        
        # Filter by doctor
        doctor_id = self.request.query_params.get('doctor')
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)
        
        return queryset