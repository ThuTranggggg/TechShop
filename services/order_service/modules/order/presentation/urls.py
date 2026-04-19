"""
Presentation URLs for Order API.

URL routing for order endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api import InternalOrderViewSet, OperationsOrderViewSet, OrderViewSet

# Create routers
router = DefaultRouter()
internal_router = DefaultRouter()
operations_router = DefaultRouter()

# Register viewsets
router.register(r"orders", OrderViewSet, basename="order")
internal_router.register(r"internal/orders", InternalOrderViewSet, basename="internal-order")
operations_router.register(r"operations/orders", OperationsOrderViewSet, basename="operations-order")

# Combine URLs
urlpatterns = [
    path("", include(router.urls)),
    path("", include(internal_router.urls)),
    path("", include(operations_router.urls)),
]
