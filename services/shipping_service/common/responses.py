from rest_framework import status
from rest_framework.response import Response


class APIResponse:
    """Standard API response wrapper."""
    
    @staticmethod
    def success(data=None, message: str = "OK", http_status: int = status.HTTP_200_OK) -> dict:
        """Create success response dict."""
        return {
            "success": True,
            "message": message,
            "data": data,
        }
    
    @staticmethod
    def error(message: str = "Error", errors=None, http_status: int = status.HTTP_400_BAD_REQUEST) -> dict:
        """Create error response dict."""
        return {
            "success": False,
            "message": message,
            "errors": errors,
        }


def success_response(message: str = "OK", data=None, http_status: int = status.HTTP_200_OK) -> Response:
    return Response(
        {
            "success": True,
            "message": message,
            "data": data,
        },
        status=http_status,
    )


def error_response(message: str = "Error", errors=None, http_status: int = status.HTTP_400_BAD_REQUEST) -> Response:
    return Response(
        {
            "success": False,
            "message": message,
            "errors": errors,
        },
        status=http_status,
    )
