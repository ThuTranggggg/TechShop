"""
Permissions for Inventory service APIs.

Handles access control for different endpoints.
"""
from rest_framework import permissions
import os


class IsInternal(permissions.BasePermission):
    """
    Permission to allow internal service-to-service requests.
    
    Checks for internal service key in header.
    """
    
    def has_permission(self, request, view):
        internal_key = os.getenv("INTERNAL_SERVICE_KEY", None)
        if not internal_key:
            # If no key configured, allow all internal requests (dev mode)
            return True
        
        provided_key = request.META.get("HTTP_X_INTERNAL_SERVICE_KEY")
        return provided_key == internal_key


class IsAdminOrStaff(permissions.BasePermission):
    """
    Permission to allow admin/staff access.
    
    Currently checks for admin=true in headers (mock auth).
    In production, integrate with proper auth service.
    """
    
    def has_permission(self, request, view):
        # In development, check for admin header
        is_admin = request.META.get("HTTP_X_ADMIN", "").lower() == "true"
        return is_admin


class IsAuthenticatedOrInternal(permissions.BasePermission):
    """
    Permission to allow authenticated users or internal services.
    """
    
    def has_permission(self, request, view):
        # Check for internal service key
        internal_key = os.getenv("INTERNAL_SERVICE_KEY", None)
        if internal_key:
            provided_key = request.META.get("HTTP_X_INTERNAL_SERVICE_KEY")
            if provided_key == internal_key:
                return True
        
        # Check for authentication token (basic mock)
        auth_header = request.META.get("HTTP_X_USER_ID")
        return bool(auth_header)
