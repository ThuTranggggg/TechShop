"""
Presentation permissions for Order API.

Permission classes for endpoint authorization.
"""

import os
from rest_framework.permissions import BasePermission
from rest_framework.request import Request


class IsAuthenticated(BasePermission):
    """
    Allow access only to authenticated users (with X-User-ID header).
    """
    
    def has_permission(self, request: Request, view) -> bool:
        user_id = request.headers.get("X-User-ID")
        return bool(user_id)


class IsOrderOwner(BasePermission):
    """
    Allow access only to order owner.
    Order owner is the user who created the order.
    """
    
    def has_permission(self, request: Request, view) -> bool:
        return bool(request.headers.get("X-User-ID"))
    
    def has_object_permission(self, request: Request, view, obj) -> bool:
        """Check if user owns the object."""
        user_id = request.headers.get("X-User-ID")
        if not user_id:
            return False
        
        # Compare user_id from order with requesting user
        return str(obj.user_id) == user_id


class IsInternalService(BasePermission):
    """
    Allow access only to internal services (with X-Internal-Service-Key header).
    
    Key is validated against INTERNAL_SERVICE_KEY env var.
    For dev, key can be empty (no auth).
    """
    
    def has_permission(self, request: Request, view) -> bool:
        # Only for internal endpoints
        if not request.path.startswith("/api/v1/internal/"):
            return True
        
        # Check for internal key
        internal_key = os.getenv("INTERNAL_SERVICE_KEY", "")
        
        # If no key configured, allow for dev
        if not internal_key:
            return True
        
        # Validate key
        provided_key = request.headers.get("X-Internal-Service-Key", "")
        return provided_key == internal_key


class IsAdminOrStaff(BasePermission):
    """
    Allow access only to admin/staff users.
    
    Checks for admin role in user claims (via gateway).
    """
    
    def has_permission(self, request: Request, view) -> bool:
        # Check for admin role
        # TODO: Validate against actual admin status from user_service
        admin_role = request.headers.get("X-User-Role", "").lower()
        return admin_role in ["admin", "staff"]
