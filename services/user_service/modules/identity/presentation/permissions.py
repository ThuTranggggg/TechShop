"""
Permission classes for Identity context API.

Defines role-based access control for different endpoints.
"""
from rest_framework import permissions
from ..domain.enums import UserRole


class IsCustomer(permissions.BasePermission):
    """Allow access only to customers."""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == UserRole.CUSTOMER
        )


class IsStaff(permissions.BasePermission):
    """Allow access only to staff members."""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == UserRole.STAFF
        )


class IsAdmin(permissions.BasePermission):
    """Allow access only to admins."""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == UserRole.ADMIN
        )


class IsStaffOrAdmin(permissions.BasePermission):
    """Allow access to staff or admin."""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in (UserRole.STAFF, UserRole.ADMIN)
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """Allow access if user is owner of the object or is admin."""
    
    def has_object_permission(self, request, view, obj):
        # Admin has access to all
        if request.user.role == UserRole.ADMIN:
            return True
        
        # Owner has access to their own data
        if hasattr(obj, "user") and obj.user == request.user:
            return True
        
        if hasattr(obj, "id") and obj.id == request.user.id:
            return True
        
        return False


class InternalServicePermission(permissions.BasePermission):
    """Permission for internal service-to-service APIs."""
    
    def has_permission(self, request, view):
        """
        Check for internal service auth.
        
        Currently checks for:
        1. X-Internal-Service header
        2. X-Internal-Token header (placeholder for future service token validation)
        
        Future: Replace with proper service-to-service auth (mTLS, JWT service tokens, etc.)
        """
        # Check for internal service header
        internal_service = request.headers.get("X-Internal-Service", "").lower()
        internal_token = request.headers.get("X-Internal-Token", "")
        
        # Placeholder: Accept any request with these headers
        # In production, validate tokens against a service registry
        if internal_service and internal_token:
            return True
        
        # For now, also deny non-authenticated internal requests
        return False
