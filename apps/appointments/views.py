# apps/appointments/views.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime, timedelta, date, time
from apps.permissions.mixins import DRFPermissionMixin, HasPermissionMixin
from .models import (
    Appointment, AppointmentType, TimeSlot, AppointmentReminder,
    AppointmentAvailability, WaitingList, AppointmentFeedback
)
from .serializers import (
    AppointmentListSerializer, AppointmentDetailSerializer, AppointmentCreateUpdateSerializer,
    CalendarEventSerializer, AppointmentTypeSerializer, TimeSlotSerializer,
    AppointmentAvailabilitySerializer, WaitingListSerializer, AppointmentFeedbackSerializer
)

class AppointmentTypeViewSet(DRFPermissionMixin, viewsets.ModelViewSet):
    queryset = AppointmentType.objects.all()
    serializer_class = AppointmentTypeSerializer
    module_name = 'appointments'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'requires_referral', 'is_emergency']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'duration_minutes', 'cost']
    ordering = ['name']

class TimeSlotViewSet(DRFPermissionMixin, viewsets.ModelViewSet):
    queryset = TimeSlot.objects.select_related('doctor__user')
    serializer_class = TimeSlotSerializer
    module_name = 'appointments'
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['doctor', 'day_of_week', 'is_available', 'is_holiday']
    ordering = ['doctor', 'day_of_week', 'start_time']

class AppointmentViewSet(DRFPermissionMixin, viewsets.ModelViewSet):
    queryset = Appointment.objects.select_related(
        'patient', 'doctor__user', 'appointment_type', 'created_by'
    ).prefetch_related('reminders', 'feedback')
    module_name = 'appointments'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'status', 'priority', 'doctor', 'patient', 'appointment_type',
        'appointment_date', 'is_follow_up', 'is_paid'
    ]
    search_fields = [
        'appointment_id', 'patient__first_name', 'patient__last_name',
        'doctor__user__first_name', 'doctor__user__last_name',
        'chief_complaint', 'symptoms'
    ]
    ordering_fields = [
        'appointment_date', 'appointment_time', 'created_at',
        'patient__first_name', 'doctor__user__first_name'
    ]
    ordering = ['appointment_date', 'appointment_time']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AppointmentListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return AppointmentCreateUpdateSerializer
        elif self.action in ['calendar_events', 'doctor_calendar', 'patient_calendar']:
            return CalendarEventSerializer
        return AppointmentDetailSerializer
    
    def get_queryset(self):
        queryset = Appointment.objects.select_related(
            'patient', 'doctor__user', 'appointment_type', 'created_by'
        ).prefetch_related('reminders', 'feedback')
        
        # Filter by date range
        from_date = self.request.query_params.get('from_date')
        to_date = self.request.query_params.get('to_date')
        if from_date:
            queryset = queryset.filter(appointment_date__gte=from_date)
        if to_date:
            queryset = queryset.filter(appointment_date__lte=to_date)
        
        # Filter by time range
        from_time = self.request.query_params.get('from_time')
        to_time = self.request.query_params.get('to_time')
        if from_time:
            queryset = queryset.filter(appointment_time__gte=from_time)
        if to_time:
            queryset = queryset.filter(appointment_time__lte=to_time)
        
        # Filter by today's appointments
        today = self.request.query_params.get('today')
        if today and today.lower() == 'true':
            queryset = queryset.filter(appointment_date=timezone.now().date())
        
        # Filter by upcoming appointments
        upcoming = self.request.query_params.get('upcoming')
        if upcoming and upcoming.lower() == 'true':
            now = timezone.now()
            queryset = queryset.filter(
                Q(appointment_date__gt=now.date()) |
                Q(appointment_date=now.date(), appointment_time__gt=now.time())
            )
        
        # Filter by past appointments
        past = self.request.query_params.get('past')
        if past and past.lower() == 'true':
            now = timezone.now()
            queryset = queryset.filter(
                Q(appointment_date__lt=now.date()) |
                Q(appointment_date=now.date(), appointment_time__lt=now.time())
            )
        
        return queryset.distinct()
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def calendar_events(self, request):
        """Get appointments formatted for calendar display"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Default to current month if no date range specified
        if not request.query_params.get('from_date'):
            today = timezone.now().date()
            start_of_month = today.replace(day=1)
            if today.month == 12:
                end_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
            
            queryset = queryset.filter(
                appointment_date__gte=start_of_month,
                appointment_date__lte=end_of_month
            )
        
        serializer = CalendarEventSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def doctor_calendar(self, request):
        """Get appointments for a specific doctor's calendar"""
        doctor_id = request.query_params.get('doctor_id')
        if not doctor_id:
            return Response({'error': 'doctor_id parameter is required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        queryset = self.filter_queryset(self.get_queryset()).filter(doctor_id=doctor_id)
        serializer = CalendarEventSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def patient_calendar(self, request):
        """Get appointments for a specific patient"""
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response({'error': 'patient_id parameter is required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        queryset = self.filter_queryset(self.get_queryset()).filter(patient_id=patient_id)
        serializer = CalendarEventSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def hospital_calendar(self, request):
        """Get all appointments for hospital-wide calendar view"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Group by doctor if requested
        group_by_doctor = request.query_params.get('group_by_doctor', 'false').lower() == 'true'
        
        if group_by_doctor:
            from django.db.models import Prefetch
            doctors = {}
            for appointment in queryset:
                doctor_id = appointment.doctor.id
                if doctor_id not in doctors:
                    doctors[doctor_id] = {
                        'doctor_id': doctor_id,
                        'doctor_name': appointment.doctor.user.get_full_name(),
                        'appointments': []
                    }
                doctors[doctor_id]['appointments'].append(
                    CalendarEventSerializer(appointment).data
                )
            return Response(list(doctors.values()))
        else:
            serializer = CalendarEventSerializer(queryset, many=True)
            return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def check_in(self, request, pk=None):
        """Check in patient for appointment"""
        appointment = self.get_object()
        
        if appointment.status != 'confirmed':
            return Response(
                {'error': 'Only confirmed appointments can be checked in'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        appointment.checked_in_at = timezone.now()
        appointment.status = 'in_progress'
        appointment.save(update_fields=['checked_in_at', 'status'])
        
        return Response({'message': 'Patient checked in successfully'})
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark appointment as completed"""
        appointment = self.get_object()
        
        if appointment.status not in ['confirmed', 'in_progress']:
            return Response(
                {'error': 'Only confirmed or in-progress appointments can be completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        appointment.status = 'completed'
        appointment.actual_end_time = timezone.now().time()
        
        # Calculate waiting time if checked in
        if appointment.checked_in_at and appointment.appointment_time:
            appointment_datetime = datetime.combine(
                appointment.appointment_date, 
                appointment.appointment_time
            )
            appointment_datetime = timezone.make_aware(appointment_datetime)
            waiting_time = appointment.checked_in_at - appointment_datetime
            appointment.waiting_time_minutes = max(0, int(waiting_time.total_seconds() / 60))
        
        appointment.save()
        
        return Response({'message': 'Appointment completed successfully'})
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel appointment"""
        appointment = self.get_object()
        
        if not appointment.can_cancel:
            return Response(
                {'error': 'Appointment cannot be cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cancellation_reason = request.data.get('reason', '')
        
        appointment.status = 'cancelled'
        appointment.cancelled_at = timezone.now()
        appointment.cancelled_by = request.user
        appointment.cancellation_reason = cancellation_reason
        appointment.save()
        
        return Response({'message': 'Appointment cancelled successfully'})
    
    @action(detail=True, methods=['post'])
    def reschedule(self, request, pk=None):
        """Reschedule appointment"""
        appointment = self.get_object()
        
        if not appointment.can_reschedule:
            return Response(
                {'error': 'Appointment cannot be rescheduled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        new_date = request.data.get('new_date')
        new_time = request.data.get('new_time')
        
        if not new_date or not new_time:
            return Response(
                {'error': 'new_date and new_time are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create new appointment
        new_appointment_data = {
            'patient': appointment.patient,
            'doctor': appointment.doctor,
            'appointment_type': appointment.appointment_type,
            'appointment_date': new_date,
            'appointment_time': new_time,
            'duration_minutes': appointment.duration_minutes,
            'chief_complaint': appointment.chief_complaint,
            'symptoms': appointment.symptoms,
            'notes': appointment.notes,
            'original_appointment': appointment,
            'created_by': request.user
        }
        
        # Validate new appointment
        serializer = AppointmentCreateUpdateSerializer(data=new_appointment_data)
        if serializer.is_valid():
            # Mark original as rescheduled
            appointment.status = 'rescheduled'
            appointment.save()
            
            # Create new appointment
            new_appointment = serializer.save()
            
            return Response({
                'message': 'Appointment rescheduled successfully',
                'new_appointment_id': new_appointment.appointment_id
            })
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def add_feedback(self, request, pk=None):
        """Add feedback for completed appointment"""
        appointment = self.get_object()
        
        if appointment.status != 'completed':
            return Response(
                {'error': 'Feedback can only be added for completed appointments'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if hasattr(appointment, 'feedback'):
            return Response(
                {'error': 'Feedback already exists for this appointment'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = request.data.copy()
        data['appointment'] = appointment.id
        
        serializer = AppointmentFeedbackSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def available_slots(self, request):
        """Get available appointment slots for a doctor"""
        doctor_id = request.query_params.get('doctor_id')
        date_param = request.query_params.get('date')
        
        if not doctor_id:
            return Response({'error': 'doctor_id parameter is required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        if not date_param:
            # Default to next 7 days
            start_date = timezone.now().date()
            end_date = start_date + timedelta(days=7)
        else:
            try:
                start_date = datetime.strptime(date_param, '%Y-%m-%d').date()
                end_date = start_date
            except ValueError:
                return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, 
                              status=status.HTTP_400_BAD_REQUEST)
        
        from apps.doctors.models import Doctor
        try:
            doctor = Doctor.objects.get(id=doctor_id)
        except Doctor.DoesNotExist:
            return Response({'error': 'Doctor not found'}, 
                          status=status.HTTP_404_NOT_FOUND)
        
        available_slots = []
        current_date = start_date
        
        while current_date <= end_date:
            day_of_week = current_date.weekday()
            
            # Get doctor's time slots for this day
            time_slots = doctor.time_slots.filter(
                day_of_week=day_of_week,
                is_available=True
            )
            
            for time_slot in time_slots:
                # Generate individual slots
                slot_start = datetime.combine(current_date, time_slot.start_time)
                slot_end = datetime.combine(current_date, time_slot.end_time)
                slot_duration = timedelta(minutes=time_slot.slot_duration)
                
                current_slot = slot_start
                while current_slot + slot_duration <= slot_end:
                    # Check if slot is available (no existing appointment)
                    existing_appointment = Appointment.objects.filter(
                        doctor=doctor,
                        appointment_date=current_date,
                        appointment_time=current_slot.time(),
                        status__in=['scheduled', 'confirmed', 'in_progress']
                    ).exists()
                    
                    if not existing_appointment:
                        available_slots.append({
                            'date': current_date.isoformat(),
                            'time': current_slot.time().isoformat(),
                            'end_time': (current_slot + slot_duration).time().isoformat(),
                            'duration_minutes': time_slot.slot_duration
                        })
                    
                    current_slot += slot_duration
            
            current_date += timedelta(days=1)
        
        return Response(available_slots)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get appointment statistics"""
        from apps.permissions.models import UserPermission
        if not UserPermission.has_permission(request.user, 'appointments.read'):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        today = timezone.now().date()
        
        # Basic counts
        total_appointments = Appointment.objects.count()
        today_appointments = Appointment.objects.filter(appointment_date=today).count()
        upcoming_appointments = Appointment.objects.filter(
            appointment_date__gte=today,
            status__in=['scheduled', 'confirmed']
        ).count()
        
        # Status distribution
        status_stats = Appointment.objects.values('status').annotate(count=Count('id'))
        
        # Monthly statistics
        current_month = today.replace(day=1)
        monthly_appointments = Appointment.objects.filter(
            appointment_date__gte=current_month
        ).count()
        
        # Average waiting time
        avg_waiting_time = Appointment.objects.filter(
            waiting_time_minutes__isnull=False
        ).aggregate(avg=Avg('waiting_time_minutes'))['avg']
        
        # Doctor utilization
        doctor_stats = Appointment.objects.filter(
            appointment_date=today
        ).values(
            'doctor__user__first_name', 
            'doctor__user__last_name'
        ).annotate(
            appointment_count=Count('id')
        ).order_by('-appointment_count')[:5]
        
        return Response({
            'total_appointments': total_appointments,
            'today_appointments': today_appointments,
            'upcoming_appointments': upcoming_appointments,
            'monthly_appointments': monthly_appointments,
            'average_waiting_time_minutes': round(avg_waiting_time, 2) if avg_waiting_time else 0,
            'status_distribution': list(status_stats),
            'top_doctors_today': list(doctor_stats)
        })

class AppointmentAvailabilityViewSet(DRFPermissionMixin, viewsets.ModelViewSet):
    queryset = AppointmentAvailability.objects.select_related('doctor__user')
    serializer_class = AppointmentAvailabilitySerializer
    module_name = 'appointments'
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['doctor', 'date', 'is_available']
    ordering = ['date', 'start_time']

class WaitingListViewSet(DRFPermissionMixin, viewsets.ModelViewSet):
    queryset = WaitingList.objects.select_related('patient', 'doctor__user', 'appointment_type')
    serializer_class = WaitingListSerializer
    module_name = 'appointments'
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['doctor', 'status', 'priority', 'preferred_date']
    ordering = ['priority', 'created_at']
    
    @action(detail=True, methods=['post'])
    def notify(self, request, pk=None):
        """Notify patient about available slot"""
        waiting_entry = self.get_object()
        
        if waiting_entry.status != 'active':
            return Response(
                {'error': 'Only active waiting list entries can be notified'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update status
        waiting_entry.status = 'notified'
        waiting_entry.notified_at = timezone.now()
        waiting_entry.save()
        
        # Here you would implement actual notification logic (SMS, Email, etc.)
        
        return Response({'message': 'Patient notified successfully'})

class AppointmentFeedbackViewSet(DRFPermissionMixin, viewsets.ModelViewSet):
    queryset = AppointmentFeedback.objects.select_related('appointment')
    serializer_class = AppointmentFeedbackSerializer
    module_name = 'appointments'
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['overall_rating', 'would_recommend', 'is_anonymous']
    ordering = ['-submitted_at']