# apps/patients/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PatientViewSet, PatientInsuranceViewSet, PatientDocumentViewSet,
    PatientVitalsViewSet, PatientAllergyViewSet, PatientMedicationViewSet,
    PatientNoteViewSet
)

router = DefaultRouter()
router.register(r'patients', PatientViewSet, basename='patient')
router.register(r'insurance', PatientInsuranceViewSet, basename='patient-insurance')
router.register(r'documents', PatientDocumentViewSet, basename='patient-document')
router.register(r'vitals', PatientVitalsViewSet, basename='patient-vitals')
router.register(r'allergies', PatientAllergyViewSet, basename='patient-allergy')
router.register(r'medications', PatientMedicationViewSet, basename='patient-medication')
router.register(r'notes', PatientNoteViewSet, basename='patient-note')

urlpatterns = [
    path('', include(router.urls)),
]
