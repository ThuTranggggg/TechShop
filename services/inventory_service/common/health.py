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
    try:
        connections["default"].cursor()
        return True
    except OperationalError:
        return False


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request, *args, **kwargs):
        payload = {
            "service": settings.SERVICE_NAME,
            "status": "healthy",
            "debug": settings.DEBUG,
        }
        return success_response(message="OK", data=payload)


class ReadyView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(responses={200: OpenApiTypes.OBJECT, 503: OpenApiTypes.OBJECT})
    def get(self, request, *args, **kwargs):
        db_ready = database_is_ready()
        payload = {
            "service": settings.SERVICE_NAME,
            "status": "ready" if db_ready else "degraded",
            "checks": {"database": db_ready},
        }
        if db_ready:
            return success_response(message="Ready", data=payload)
        return error_response(
            message="Database unavailable",
            errors=payload,
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
