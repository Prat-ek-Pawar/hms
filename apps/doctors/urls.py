from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DoctorViewSet, SpecialtyViewSet, QualificationViewSet, HospitalViewSet,
    DoctorExperienceViewSet, DoctorAvailabilityViewSet, DoctorReviewViewSet
)

router = DefaultRouter()
router.register(r'doctors', DoctorViewSet, basename='doctor')
router.register(r'specialties', SpecialtyViewSet, basename='specialty')
router.register(r'qualifications', QualificationViewSet, basename='qualification')
router.register(r'hospitals', HospitalViewSet, basename='hospital')
router.register(r'experiences', DoctorExperienceViewSet, basename='doctor-experience')
router.register(r'availability', DoctorAvailabilityViewSet, basename='doctor-availability')
router.register(r'reviews', DoctorReviewViewSet, basename='doctor-review')

urlpatterns = [
    path('', include(router.urls)),
]