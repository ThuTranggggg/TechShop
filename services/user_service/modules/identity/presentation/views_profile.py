"""
Profile views for Identity context.

Handles user profile and address management for authenticated users.
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from common.responses import success_response, error_response
from ..infrastructure.models import User, Address
from .serializers import (
    UserProfileSerializer,
    UserProfileUpdateSerializer,
    AddressSerializer,
)
from .permissions import IsOwnerOrAdmin


class ProfileViewSet(viewsets.ViewSet):
    """User profile management."""
    
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def profile(self, request):
        """Get current user profile."""
        serializer = UserProfileSerializer(request.user)
        
        return success_response(
            message="User profile",
            data=serializer.data,
            http_status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=["patch"], permission_classes=[IsAuthenticated])
    def update_profile(self, request):
        """Update current user profile (limited fields)."""
        serializer = UserProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return success_response(
                message="Profile updated successfully",
                data=UserProfileSerializer(request.user).data,
                http_status=status.HTTP_200_OK
            )
        
        return error_response(
            message="Profile update failed",
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class AddressViewSet(viewsets.ModelViewSet):
    """User address management (CRUD)."""
    
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["address_type", "is_default"]
    
    def get_queryset(self):
        """Get addresses for the current user."""
        return Address.objects.filter(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """Create a new address for the current user."""
        data = request.data.copy()
        data["user"] = request.user.id
        
        serializer = self.get_serializer(data=data)
        
        if serializer.is_valid():
            serializer.save()
            return success_response(
                message="Address created successfully",
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        
        return error_response(
            message="Address creation failed",
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )
    
    def list(self, request, *args, **kwargs):
        """List all addresses for the current user."""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        
        return success_response(
            message="User addresses",
            data=serializer.data,
            http_status=status.HTTP_200_OK
        )
    
    def retrieve(self, request, *args, **kwargs):
        """Get a specific address."""
        address = self.get_object()
        
        # Check ownership
        if address.user != request.user:
            return error_response(
                message="Access denied",
                http_status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(address)
        
        return success_response(
            message="Address details",
            data=serializer.data,
            http_status=status.HTTP_200_OK
        )
    
    def update(self, request, *args, **kwargs):
        """Update an address."""
        address = self.get_object()
        
        # Check ownership
        if address.user != request.user:
            return error_response(
                message="Access denied",
                http_status=status.HTTP_403_FORBIDDEN
            )
        
        data = request.data.copy()
        # Prevent user from changing ownership
        data["user"] = address.user.id
        
        serializer = self.get_serializer(address, data=data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return success_response(
                message="Address updated successfully",
                data=serializer.data,
                http_status=status.HTTP_200_OK
            )
        
        return error_response(
            message="Address update failed",
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )
    
    def destroy(self, request, *args, **kwargs):
        """Delete an address."""
        address = self.get_object()
        
        # Check ownership
        if address.user != request.user:
            return error_response(
                message="Access denied",
                http_status=status.HTTP_403_FORBIDDEN
            )
        
        address.delete()
        
        return success_response(
            message="Address deleted successfully",
            http_status=status.HTTP_204_NO_CONTENT
        )
    
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def set_default(self, request, pk=None):
        """Set an address as default."""
        address = self.get_object()
        
        # Check ownership
        if address.user != request.user:
            return error_response(
                message="Access denied",
                http_status=status.HTTP_403_FORBIDDEN
            )
        
        # Set as default (model's save method will handle removing other defaults)
        address.is_default = True
        address.save()
        
        serializer = self.get_serializer(address)
        
        return success_response(
            message="Address set as default",
            data=serializer.data,
            http_status=status.HTTP_200_OK
        )
