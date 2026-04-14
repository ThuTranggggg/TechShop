"""
Internal service API views for Identity context.

These endpoints are for inter-service communication only.
They are protected with internal service authentication headers.

Protection mechanism:
- Requires X-Internal-Service and X-Internal-Token headers
- Currently placeholder; will be upgraded to mTLS/JWT service tokens in production
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.responses import success_response, error_response
from ..infrastructure.models import User
from .serializers import (
    InternalUserBasicSerializer,
    InternalUserBulkSerializer,
    InternalUserStatusSerializer,
)
from .permissions import InternalServicePermission


class InternalUserViewSet(viewsets.ViewSet):
    """Internal service endpoints for user information."""
    
    permission_classes = [InternalServicePermission]
    
    @action(detail=False, methods=["get"], permission_classes=[InternalServicePermission])
    def get_user_by_id(self, request):
        """Get basic user info by ID (internal only)."""
        user_id = request.query_params.get("user_id")
        
        if not user_id:
            return error_response(
                message="user_id parameter is required",
                http_status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return error_response(
                message="User not found",
                http_status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = InternalUserBasicSerializer(user)
        
        return success_response(
            message="User info",
            data=serializer.data,
            http_status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=["post"], permission_classes=[InternalServicePermission])
    def get_bulk_users(self, request):
        """Get multiple users by IDs (internal only)."""
        serializer = InternalUserBulkSerializer(data=request.data)
        
        if not serializer.is_valid():
            return error_response(
                message="Invalid request",
                errors=serializer.errors,
                http_status=status.HTTP_400_BAD_REQUEST
            )
        
        user_ids = serializer.validated_data["user_ids"]
        users = User.objects.filter(id__in=user_ids)
        
        data = InternalUserBasicSerializer(users, many=True).data
        
        return success_response(
            message="Users info",
            data=data,
            http_status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=["get"], permission_classes=[InternalServicePermission])
    def get_user_status(self, request):
        """Get user active/verified status (internal only)."""
        user_id = request.query_params.get("user_id")
        
        if not user_id:
            return error_response(
                message="user_id parameter is required",
                http_status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return error_response(
                message="User not found",
                http_status=status.HTTP_404_NOT_FOUND
            )
        
        data = {
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "role": user.role,
        }
        
        return success_response(
            message="User status",
            data=data,
            http_status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=["get"], permission_classes=[InternalServicePermission])
    def validate_user_active(self, request):
        """Validate if user is active (internal only)."""
        user_id = request.query_params.get("user_id")
        
        if not user_id:
            return error_response(
                message="user_id parameter is required",
                http_status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return error_response(
                message="User not found",
                http_status=status.HTTP_404_NOT_FOUND
            )
        
        if not user.is_active:
            return error_response(
                message="User is not active",
                http_status=status.HTTP_403_FORBIDDEN
            )
        
        return success_response(
            message="User is active",
            data={"user_id": str(user.id), "is_active": True},
            http_status=status.HTTP_200_OK
        )
