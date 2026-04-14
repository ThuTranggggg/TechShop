# Django Microservices Foundation Standardization Guide

## Tổng quan công việc đã làm

### ✅ Đã hoàn thành
1. **Settings.py** - Toàn bộ 8 services đã có config env-based đầy đủ
2. **Common modules base** - responses.py, exceptions.py, health.py, logging.py đã tồn tại
3. **URL routing** - Toàn bộ services có /health/, /api/v1/health/, /api/schema/, /api/docs/
4. **.env.example** - Đã tạo cho tất cả services
5. **Dockerfiles** - Toàn bộ services có Dockerfile đúng cách
6. **docker-compose** - Đã có định nghĩa hoàn chỉnh cho tất cả 8 services
7. **Nginx gateway** - Routing cơ bản đã setup

## 📋 Danh sách Services
- ✅ user_service (port 8001)
- ✅ product_service (port 8002)
- ✅ cart_service (port 8003)
- ✅ order_service (port 8004)
- ✅ payment_service (port 8005)
- ✅ shipping_service (port 8006)
- ✅ inventory_service (port 8007)
- ✅ ai_service (port 8008)

## 🔧 Standardized Common Modules

### 1. common/responses.py (STANDARDIZED - áp dụng cho tất cả services)
```python
"""
Standardized response helpers for consistent API responses across the service.
"""
from typing import Any, Dict, Optional

from rest_framework import status
from rest_framework.response import Response


def success_response(
    message: str = "OK",
    data: Optional[Any] = None,
    http_status: int = status.HTTP_200_OK,
) -> Response:
    """
    Create a standardized success response.
    
    Args:
        message: Human-readable success message
        data: Response payload data
        http_status: HTTP status code
        
    Returns:
        DRF Response object with standardized format
    """
    return Response(
        {
            "success": True,
            "message": message,
            "data": data,
        },
        status=http_status,
    )


def error_response(
    message: str = "Error",
    errors: Optional[Dict[str, Any]] = None,
    http_status: int = status.HTTP_400_BAD_REQUEST,
) -> Response:
    """
    Create a standardized error response.
    
    Args:
        message: Human-readable error message
        errors: Error details dictionary
        http_status: HTTP error status code
        
    Returns:
        DRF Response object with standardized format
    """
    return Response(
        {
            "success": False,
            "message": message,
            "errors": errors or {},
        },
        status=http_status,
    )


def paginated_response(
    message: str = "OK",
    data: Optional[list] = None,
    pagination: Optional[Dict[str, Any]] = None,
    http_status: int = status.HTTP_200_OK,
) -> Response:
    """
    Create a standardized paginated response.
    
    Args:
        message: Human-readable message
        data: List of items in current page
        pagination: Pagination metadata (count, next, previous, page_size, etc.)
        http_status: HTTP status code
        
    Returns:
        DRF Response object with standardized format
    """
    return Response(
        {
            "success": True,
            "message": message,
            "data": data or [],
            "pagination": pagination or {},
        },
        status=http_status,
    )
```

### 2. common/exceptions.py (STANDARDIZED - áp dụng cho tất cả services)
```python
"""
Custom exceptions and DRF exception handler for consistent error handling.
"""
from typing import Optional

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler

from common.responses import error_response


class ServiceException(APIException):
    """Base exception for service-specific errors."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Service exception"
    default_code = "service_exception"


class ValidationException(ServiceException):
    """Raised when validation fails."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Validation error"
    default_code = "validation_error"


class NotFoundException(ServiceException):
    """Raised when requested resource is not found."""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Resource not found"
    default_code = "not_found"


class ConflictException(ServiceException):
    """Raised when there's a conflict (e.g., duplicate entry)."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Resource conflict"
    default_code = "conflict"


class UnauthorizedException(ServiceException):
    """Raised when authentication is required but not provided."""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Authentication required"
    default_code = "unauthorized"


class ForbiddenException(ServiceException):
    """Raised when user is not allowed to access resource."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Access forbidden"
    default_code = "forbidden"


class ExternalServiceException(ServiceException):
    """Raised when an external service call fails."""
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "External service error"
    default_code = "external_service_error"


def custom_exception_handler(exc, context):
    """
    Custom exception handler for consistent error response format.
    
    Wraps DRF's default exception handler to ensure all errors follow
    the standardized error response format.
    
    Args:
        exc: The exception being handled
        context: Additional context about the exception
        
    Returns:
        Response object with standardized error format
    """
    response = exception_handler(exc, context)
    
    if response is not None:
        # Handle DRF exceptions
        error_detail = response.data
        
        # Format error detail
        if isinstance(error_detail, dict):
            # Multiple errors
            errors = error_detail
        elif isinstance(error_detail, list):
            # List of errors (usually from list validators)
            errors = {f"error_{i}": str(e) for i, e in enumerate(error_detail)}
        else:
            # Single error
            errors = {"detail": str(error_detail)}
        
        return error_response(
            message=str(error_detail) if isinstance(error_detail, str) else "Request failed",
            errors=errors,
            http_status=response.status_code,
        )
    
    # Handle unexpected errors
    return error_response(
        message="Internal server error",
        errors={"detail": str(exc)},
        http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
```

### 3. common/logging.py (STANDARDIZED - áp dụng cho tất cả services)
```python
"""
Structured logging utilities for consistent logging across the service.
"""
import json
import logging
from typing import Any, Dict, Optional


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that adds structured logging with service context.
    
    Adds service name, environment, and other metadata to log records.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as structured output with metadata.
        
        Args:
            record: The log record to format
            
        Returns:
            Formatted log message
        """
        # Create base formatted message
        base_message = super().format(record)
        
        # Add service context
        service_name = getattr(record, "service", "django")
        
        # Build enhanced message with common metadata
        enhanced_message = f"[{service_name}] {base_message}"
        
        # Add traceback if present
        if record.exc_info:
            enhanced_message += f" | exc_info={record.exc_info}"
        
        return enhanced_message


class ContextualLogger:
    """
    Wrapper around Python logger to add contextual information to logs.
    
    Usage:
        logger = ContextualLogger.get_logger(__name__)
        logger.info("User action", {"user_id": 123, "ip": "192.168.1.1"})
    """
    
    _loggers = {}
    
    @classmethod
    def get_logger(cls, name: str) -> "ContextualLogger":
        """Get or create a logger instance."""
        if name not in cls._loggers:
            cls._loggers[name] = cls(name)
        return cls._loggers[name]
    
    def __init__(self, name: str):
        """Initialize logger."""
        self.logger = logging.getLogger(name)
    
    def _log_with_context(
        self,
        level: int,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Internal method to log with context."""
        if context:
            # Format context as readable string
            context_str = ", ".join(
                f"{key}={value}" for key, value in context.items()
            )
            message = f"{message} | context: {context_str}"
        self.logger.log(level, message)
    
    def debug(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log debug message with optional context."""
        self._log_with_context(logging.DEBUG, message, context)
    
    def info(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log info message with optional context."""
        self._log_with_context(logging.INFO, message, context)
    
    def warning(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log warning message with optional context."""
        self._log_with_context(logging.WARNING, message, context)
    
    def error(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log error message with optional context."""
        self._log_with_context(logging.ERROR, message, context)
    
    def critical(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log critical message with optional context."""
        self._log_with_context(logging.CRITICAL, message, context)
```

### 4. common/health.py (STANDARDIZED - áp dụng cho tất cả services)
```python
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
```

### 5. common/__init__.py (CREATE if not exists)
```python
"""
Common utilities and helpers shared across all modules.
"""
```

## 📝 Hướng dẫn áp dụng cho mỗi service

**Cho tất cả 8 services (user, product, cart, order, payment, shipping, inventory, ai):**

1. Thay thế content của `common/responses.py` với version standardized ở trên
2. Thay thế content của `common/exceptions.py` với version standardized ở trên
3. Thay thế content của `common/logging.py` với version standardized ở trên
4. Thay thế content của `common/health.py` với version standardized ở trên
5. Tạo file `common/__init__.py` nếu chưa có

## ✅ Verification Checklist

### Settings.py đã có
- [x] SECRET_KEY từ env
- [x] DEBUG từ env
- [x] ALLOWED_HOSTS từ env
- [x] SERVICE_NAME, SERVICE_PORT từ env
- [x] Database config từ env
- [x] REDIS_URL từ env
- [x] NEO4J config từ env
- [x] INSTALLED_APPS đầy đủ (admin, auth, rest_framework, drf_spectacular, django_filters)
- [x] MIDDLEWARE chuẩn
- [x] REST_FRAMEWORK config với custom exception handler
- [x] SPECTACULAR_SETTINGS cho API schema
- [x] LOGGING config đầy đủ

### URL Routing
- [x] `/health/` - Health check
- [x] `/ready/` - Readiness check
- [x] `/api/v1/health/` - Api v1 health
- [x] `/api/schema/` - OpenAPI schema
- [x] `/api/docs/` - Swagger UI docs
- [x] `/admin/` - Django admin

### Response Format
- [x] Success responses: `{success: true, message, data}`
- [x] Error responses: `{success: false, message, errors}`
- [x] Paginated responses: `{success: true, message, data[], pagination{}}`

### Exception Handling
- [x] Custom exception handler installed
- [x] ServiceException base class
- [x] Specific exceptions (NotFoundException, ValidationException, etc.)

### Database & Infrastructure
- [x] PostgreSQL connection per service
- [x] Redis support
- [x] Neo4j support
- [x] ENV variable support for all configs

---

## 🚀 Các bước tiếp theo (After Foundation)

1. **Add meaningful models** - Tạo DDD-aligned models cho mỗi service
2. **Implement serializers** - DRF serializers cho mỗi model
3. **Create viewsets và routes** - API endpoints cho business logic
4. **Add permissions & auth** - Token auth cho request
5. **Implement service layer** - Business logic separation
6. **Add integration tests** - Test service endpoints
7. **Setup CI/CD** - GitHub Actions hoặc tương tự

---

## 📞 Notes

- Tất cả settings đã support env variables từ `.env` file hoặc environment
- Tất cả responses tuân theo format chuẩn
- Logging đã setup với structured format
- Health checks hoạt động cho Docker healthchecks
- Schema docs đã enable qua drf_spectacular
- Toàn bộ stack sẵn sàng cho `docker-compose up`

**Lưu ý:** Foundation này đủ sạch và flexible để bắt đầu phát triển domain logic mà không cần refactor lại nền tảng.
