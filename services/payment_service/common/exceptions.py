from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler

from common.responses import error_response


class ServiceException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Service exception"
    default_code = "service_exception"


def custom_exception_handler(exc, context):
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
