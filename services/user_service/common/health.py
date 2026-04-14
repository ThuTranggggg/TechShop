"""
Health and readiness check endpoints for service monitoring.
"""
from django.conf import settings
from django.db import connections
from django.db.utils import OperationalError
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from common.responses import error_response, success_response


def database_is_ready() -> bool:
    """
    Check if database connection is ready.

    Returns:
        True if database connection is successful, False otherwise
    """
    try:
        connections["default"].cursor()
        return True
    except OperationalError:
        return False


class HealthView(APIView):
    """
    Simple health check endpoint.

    Returns 200 OK with service name and status.
    Used by container orchestrators and load balancers.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        responses={200: OpenApiTypes.OBJECT},
        tags=["health"],
        description="Health check endpoint - always returns 200 if service is running",
    )
    def get(self, request, *args, **kwargs):
        """Get health status of the service."""
        payload = {
            "service": settings.SERVICE_NAME,
            "status": "healthy",
            "debug": settings.DEBUG,
        }
        return success_response(message="Service is healthy", data=payload)


class ReadyView(APIView):
    """
    Readiness check endpoint.

    Returns 200 OK if service is ready to handle requests (including DB connectivity).
    Returns 503 Service Unavailable if service is not ready.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        responses={
            200: OpenApiTypes.OBJECT,
            503: OpenApiTypes.OBJECT,
        },
        tags=["health"],
        description="Readiness check - returns 200 if service is ready, 503 if not ready",
    )
    def get(self, request, *args, **kwargs):
        """Get readiness status of the service."""
        db_ready = database_is_ready()
        payload = {
            "service": settings.SERVICE_NAME,
            "status": "ready" if db_ready else "degraded",
            "checks": {
                "database": "ok" if db_ready else "unavailable",
            },
        }

        if db_ready:
            return success_response(
                message="Service is ready",
                data=payload,
                http_status=status.HTTP_200_OK,
            )

        return error_response(
            message="Service not ready - database unavailable",
            errors={"database": "connection failed"},
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
