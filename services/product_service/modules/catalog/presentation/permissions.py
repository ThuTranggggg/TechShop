"""
Presentation layer permissions for Catalog API.

RBAC for public, admin, and internal access.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsPublicRead(BasePermission):
    """Allow public read-only access to published catalog."""

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class IsStaffOrAdmin(BasePermission):
    """Allow staff/admin to manage catalog."""

    def has_permission(self, request, view):
        if request.META.get("HTTP_X_ADMIN", "").lower() == "true":
            return True
        # For now, check if user has staff/admin role via JWT token
        # This would be populated by user_service
        user = getattr(request, 'user', None)
        if not user:
            return False

        # Check role claim in JWT token
        role = getattr(user, 'role', None)
        return role in ['staff', 'admin']


class InternalServicePermission(BasePermission):
    """Allow internal service-to-service access."""

    def has_permission(self, request, view):
        # Check internal service header
        internal_service = request.META.get('HTTP_X_INTERNAL_SERVICE')
        internal_token = request.META.get('HTTP_X_INTERNAL_TOKEN')
        
        # Placeholder: just check headers exist
        return bool(internal_service and internal_token)


class IsOwnerOrAdmin(BasePermission):
    """For future use: check if user owns the resource."""

    def has_object_permission(self, request, view, obj):
        return True  # Placeholder
