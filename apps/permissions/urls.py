# apps/permissions/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ModuleViewSet, PermissionViewSet, UserGroupViewSet,
    UserPermissionViewSet, PermissionLogViewSet
)

router = DefaultRouter()
router.register(r'modules', ModuleViewSet, basename='module')
router.register(r'permissions', PermissionViewSet, basename='permission')
router.register(r'groups', UserGroupViewSet, basename='usergroup')
router.register(r'user-permissions', UserPermissionViewSet, basename='userpermission')
router.register(r'logs', PermissionLogViewSet, basename='permissionlog')

urlpatterns = [
    path('', include(router.urls)),
]