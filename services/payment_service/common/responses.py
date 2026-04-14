from rest_framework import status
from rest_framework.response import Response


class APIResponse:
    """Backward-compatible response payload helper."""

    @staticmethod
    def success(data=None, message: str = "OK"):
        return {
            "success": True,
            "message": message,
            "data": data,
        }

    @staticmethod
    def error(message: str = "Error", errors=None):
        return {
            "success": False,
            "message": message,
            "errors": errors,
        }


def success_response(message: str = "OK", data=None, http_status: int = status.HTTP_200_OK) -> Response:
    return Response(APIResponse.success(data=data, message=message), status=http_status)


def error_response(message: str = "Error", errors=None, http_status: int = status.HTTP_400_BAD_REQUEST) -> Response:
    return Response(APIResponse.error(message=message, errors=errors), status=http_status)
