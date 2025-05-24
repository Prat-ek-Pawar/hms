# apps/appointments/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AppointmentViewSet, AppointmentTypeViewSet, TimeSlotViewSet,
    AppointmentAvailabilityViewSet, WaitingListViewSet, AppointmentFeedbackViewSet
)

router = DefaultRouter()
router.register(r'appointments', AppointmentViewSet, basename='appointment')
router.register(r'types', AppointmentTypeViewSet, basename='appointment-type')
router.register(r'timeslots', TimeSlotViewSet, basename='timeslot')
router.register(r'availability', AppointmentAvailabilityViewSet, basename='appointment-availability')
router.register(r'waiting-list', WaitingListViewSet, basename='waiting-list')
router.register(r'feedback', AppointmentFeedbackViewSet, basename='appointment-feedback')

urlpatterns = [
    path('', include(router.urls)),
]
