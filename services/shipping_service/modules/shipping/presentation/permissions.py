"""
Shipment Module - Permissions

Authorization and access control.
"""

from rest_framework.permissions import BasePermission
from django.conf import settings


class IsInternalService(BasePermission):
    """
    Allow access only if request contains valid internal service key.
    
    Used for service-to-service communication (e.g., order_service calling shipping_service).
    """
    
    def has_permission(self, request, view):
        # Allow if internal key header matches
        internal_key = request.META.get("HTTP_X_INTERNAL_SERVICE_KEY", "")
        expected_key = getattr(settings, "INTERNAL_SERVICE_KEY", "dev-key-change-in-production")
        
        # In development, allow from localhost
        if settings.DEBUG:
            client_ip = self.get_client_ip(request)
            if client_ip in ("127.0.0.1", "localhost", "127.0.0.1:8000"):
                return True
        
        return internal_key == expected_key
    
    @staticmethod
    def get_client_ip(request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip


class IsMockServiceEnabled(BasePermission):
    """
    Allow access to mock endpoints only if DEBUG=True or X-Mock-Enabled header is present.
    
    Used to protect development/testing endpoints that should not be accessible in production.
    """
    
    def has_permission(self, request, view):
        # Allow in debug mode
        if settings.DEBUG:
            return True
        
        # Allow if mock header is explicitly set
        mock_enabled = request.META.get("HTTP_X_MOCK_ENABLED", "").lower() == "true"
        return mock_enabled


class AllowAny(BasePermission):
    """
    Allow any access.
    
    Used for public endpoints (customer tracking).
    """
    
    def has_permission(self, request, view):
        return True


class IsAdminOrStaff(BasePermission):
    """Allow staff/admin operational access through gateway headers."""

    def has_permission(self, request, view):
        role = request.META.get("HTTP_X_USER_ROLE", "").lower()
        if role in {"admin", "staff"}:
            return True
        return request.META.get("HTTP_X_ADMIN", "").lower() == "true"
