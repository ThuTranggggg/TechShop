"""
Permissions for Cart service APIs.

Handles access control for different endpoints.
"""
from rest_framework import permissions
import os


class IsCartOwner(permissions.BasePermission):
    """
    Permission to verify user is cart owner.
    
    Used for user-specific cart endpoints.
    """
    
    def has_permission(self, request, view):
        # Extract user_id from path or request
        user_id = request.resolver_match.kwargs.get("user_id")
        auth_user = getattr(request, "user", None)
        
        # In dev mode, check header
        header_user = request.META.get("HTTP_X_USER_ID")
        if header_user:
            return header_user == user_id
        
        return False


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


class IsAuthenticatedCustomer(permissions.BasePermission):
    """
    Permission to allow authenticated customers.
    """
    
    def has_permission(self, request, view):
        # Check for user ID in header (mock auth)
        user_id = request.META.get("HTTP_X_USER_ID")
        return bool(user_id)
