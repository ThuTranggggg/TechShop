"""
Admin user management views for Identity context.

Handles admin/staff operations for user management.
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend

from common.responses import success_response, error_response
from ..infrastructure.models import User, Address
from ..domain.enums import UserRole
from .serializers import (
    AdminUserListSerializer,
    AdminUserDetailSerializer,
    AdminUserUpdateSerializer,
    AdminUserRoleChangeSerializer,
    AddressSerializer,
)
from .permissions import IsStaffOrAdmin


class AdminUserViewSet(viewsets.ViewSet):
    """Admin user management endpoints."""
    
    permission_classes = [IsAuthenticated, IsStaffOrAdmin]
    
    def get_queryset(self):
        """Get all users."""
        return User.objects.all()
    
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated, IsStaffOrAdmin])
    def list_users(self, request):
        """List all users with filtering and search."""
        queryset = self.get_queryset()
        
        # Search
        search_query = request.query_params.get("search", "").strip()
        if search_query:
            queryset = queryset.filter(
                Q(email__icontains=search_query) |
                Q(full_name__icontains=search_query) |
                Q(phone_number__icontains=search_query)
            )
        
        # Filter by role
        role_filter = request.query_params.get("role", "").strip()
        if role_filter in [role.value for role in UserRole]:
            queryset = queryset.filter(role=role_filter)
        
        # Filter by status
        is_active_filter = request.query_params.get("is_active", "").strip().lower()
        if is_active_filter in ("true", "1", "yes"):
            queryset = queryset.filter(is_active=True)
        elif is_active_filter in ("false", "0", "no"):
            queryset = queryset.filter(is_active=False)
        
        # Ordering
        ordering = request.query_params.get("ordering", "-created_at").strip()
        if ordering in ("created_at", "-created_at", "email", "-email", "updated_at", "-updated_at"):
            queryset = queryset.order_by(ordering)
        
        # Pagination
        page_size = int(request.query_params.get("page_size", 20))
        page = int(request.query_params.get("page", 1)) - 1
        
        total_count = queryset.count()
        users = queryset[page * page_size:(page + 1) * page_size]
        
        serializer = AdminUserListSerializer(users, many=True)
        
        return success_response(
            message="Users list",
            data={
                "count": total_count,
                "page": page + 1,
                "page_size": page_size,
                "results": serializer.data,
            },
            http_status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated, IsStaffOrAdmin])
    def user_detail(self, request):
        """Get details of a specific user."""
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
        
        serializer = AdminUserDetailSerializer(user)
        
        return success_response(
            message="User details",
            data=serializer.data,
            http_status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=["patch"], permission_classes=[IsAuthenticated, IsStaffOrAdmin])
    def update_user(self, request):
        """Update a user's profile (by admin/staff)."""
        user_id = request.data.get("user_id")
        
        if not user_id:
            return error_response(
                message="user_id is required",
                http_status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return error_response(
                message="User not found",
                http_status=status.HTTP_404_NOT_FOUND
            )
        
        # Remove user_id from data before validation
        data = {k: v for k, v in request.data.items() if k != "user_id"}
        
        serializer = AdminUserUpdateSerializer(user, data=data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return success_response(
                message="User updated successfully",
                data=AdminUserDetailSerializer(user).data,
                http_status=status.HTTP_200_OK
            )
        
        return error_response(
            message="User update failed",
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated, IsStaffOrAdmin])
    def deactivate_user(self, request):
        """Deactivate a user account."""
        user_id = request.data.get("user_id")
        
        if not user_id:
            return error_response(
                message="user_id is required",
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
                message="User is already deactivated",
                http_status=status.HTTP_400_BAD_REQUEST
            )
        
        # Prevent users from deactivating themselves or admins without sufficient rights
        if user == request.user:
            return error_response(
                message="Cannot deactivate yourself",
                http_status=status.HTTP_400_BAD_REQUEST
            )
        
        if user.is_admin and not request.user.is_admin:
            return error_response(
                message="Only admins can deactivate other admins",
                http_status=status.HTTP_403_FORBIDDEN
            )
        
        user.is_active = False
        user.save(update_fields=["is_active"])
        
        return success_response(
            message="User deactivated successfully",
            data=AdminUserDetailSerializer(user).data,
            http_status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated, IsStaffOrAdmin])
    def activate_user(self, request):
        """Activate a user account."""
        user_id = request.data.get("user_id")
        
        if not user_id:
            return error_response(
                message="user_id is required",
                http_status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return error_response(
                message="User not found",
                http_status=status.HTTP_404_NOT_FOUND
            )
        
        if user.is_active:
            return error_response(
                message="User is already active",
                http_status=status.HTTP_400_BAD_REQUEST
            )
        
        user.is_active = True
        user.save(update_fields=["is_active"])
        
        return success_response(
            message="User activated successfully",
            data=AdminUserDetailSerializer(user).data,
            http_status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated, IsStaffOrAdmin])
    def change_role(self, request):
        """Change a user's role."""
        user_id = request.data.get("user_id")
        
        if not user_id:
            return error_response(
                message="user_id is required",
                http_status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return error_response(
                message="User not found",
                http_status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = AdminUserRoleChangeSerializer(data=request.data)
        
        if not serializer.is_valid():
            return error_response(
                message="Invalid role",
                errors=serializer.errors,
                http_status=status.HTTP_400_BAD_REQUEST
            )
        
        new_role = serializer.validated_data["role"]
        
        # Check permissions
        if new_role == UserRole.ADMIN and not request.user.is_admin:
            return error_response(
                message="Only admins can promote users to admin",
                http_status=status.HTTP_403_FORBIDDEN
            )
        
        if user.role == UserRole.ADMIN and not request.user.is_admin:
            return error_response(
                message="Only admins can change admin role",
                http_status=status.HTTP_403_FORBIDDEN
            )
        
        user.role = new_role
        user.is_staff = new_role == UserRole.ADMIN or new_role == UserRole.STAFF
        user.save(update_fields=["role", "is_staff"])
        
        return success_response(
            message="User role changed successfully",
            data=AdminUserDetailSerializer(user).data,
            http_status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated, IsStaffOrAdmin])
    def user_addresses(self, request):
        """Get all addresses of a specific user."""
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
        
        addresses = Address.objects.filter(user=user)
        serializer = AddressSerializer(addresses, many=True)
        
        return success_response(
            message="User addresses",
            data=serializer.data,
            http_status=status.HTTP_200_OK
        )
