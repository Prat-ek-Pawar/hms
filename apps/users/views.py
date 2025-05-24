# apps/users/views.py
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from django.contrib.auth import login, logout
from django.contrib.auth.models import Group
from django.db.models import Q
from apps.permissions.mixins import HasPermissionMixin, DRFPermissionMixin
from apps.permissions.models import UserPermission
from .models import User
from .serializers import (
    UserSerializer, UserCreateSerializer, UserUpdateSerializer,
    ChangePasswordSerializer, LoginSerializer
)

class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        token, created = Token.objects.get_or_create(user=user)
        login(request, user)
        
        return Response({
            'token': token.key,
            'user': UserSerializer(user, context={'request': request}).data
        })

class LogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            request.user.auth_token.delete()
        except:
            pass
        logout(request)
        return Response({'message': 'Successfully logged out'})

class UserViewSet(DRFPermissionMixin, viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    module_name = 'users'  # This will create permissions like 'users.create', 'users.read', etc.
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer
    
    def get_queryset(self):
        queryset = User.objects.all()
        
        # Filter by role
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        
        # Filter by department
        department = self.request.query_params.get('department')
        if department:
            queryset = queryset.filter(department__icontains=department)
        
        # Search functionality
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(employee_id__icontains=search)
            )
        
        # Filter active/inactive users
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset.order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user's profile"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def change_password(self, request, pk=None):
        """Change user password"""
        user = self.get_object()
        
        # Only allow users to change their own password or admins to change any password
        if user != request.user and not request.user.is_superuser:
            if not UserPermission.has_permission(request.user, 'users.update'):
                return Response(
                    {'error': 'Permission denied'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            # Check old password only if user is changing their own password
            if user == request.user:
                if not user.check_password(serializer.validated_data['old_password']):
                    return Response(
                        {'error': 'Invalid old password'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            return Response({'message': 'Password changed successfully'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def add_to_group(self, request, pk=None):
        """Add user to a group"""
        user = self.get_object()
        group_id = request.data.get('group_id')
        
        if not group_id:
            return Response(
                {'error': 'group_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            group = Group.objects.get(id=group_id)
            user.groups.add(group)
            return Response({'message': f'User added to group {group.name}'})
        except Group.DoesNotExist:
            return Response(
                {'error': 'Group not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def remove_from_group(self, request, pk=None):
        """Remove user from a group"""
        user = self.get_object()
        group_id = request.data.get('group_id')
        
        if not group_id:
            return Response(
                {'error': 'group_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            group = Group.objects.get(id=group_id)
            user.groups.remove(group)
            return Response({'message': f'User removed from group {group.name}'})
        except Group.DoesNotExist:
            return Response(
                {'error': 'Group not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def permissions(self, request, pk=None):
        """Get user's effective permissions"""
        user = self.get_object()
        permissions = user.get_user_permissions_list()
        return Response({'permissions': permissions})
    
    @action(detail=False, methods=['get'])
    def roles(self, request):
        """Get available user roles"""
        return Response({'roles': dict(User.ROLE_CHOICES)})
    
    @action(detail=False, methods=['get'])
    def departments(self, request):
        """Get list of departments"""
        departments = User.objects.exclude(
            department__isnull=True
        ).exclude(
            department__exact=''
        ).values_list('department', flat=True).distinct()
        
        return Response({'departments': list(departments)})

class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user

