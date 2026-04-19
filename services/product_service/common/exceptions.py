from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404

from common.responses import error_response


class ServiceException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Service exception"
    default_code = "service_exception"


def custom_exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        error_payload = exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages if hasattr(exc, "messages") else [str(exc)]}
        return error_response(
            message="Request failed",
            errors=error_payload,
            http_status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, Http404):
        return error_response(
            message="Resource not found",
            errors={"detail": [str(exc) or "Not found"]},
            http_status=status.HTTP_404_NOT_FOUND,
        )

    response = exception_handler(exc, context)
    if response is not None:
        return error_response(
            message="Request failed",
            errors=response.data,
            http_status=response.status_code,
        )
    return error_response(
        message="Internal server error",
        errors={"detail": str(exc)},
        http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
