"""
Presentation layer for Order context.

Contains API views, serializers, permissions, and URL routing.
"""

from .api import OrderViewSet, InternalOrderViewSet
from .serializers import (
    OrderDetailSerializer, OrderListItemSerializer, CreateOrderFromCartSerializer,
    OrderTimelineSerializer
)
from .permissions import IsAuthenticated, IsOrderOwner, IsInternalService, IsAdminOrStaff

__all__ = [
    # Views
    "OrderViewSet",
    "InternalOrderViewSet",
    # Serializers
    "OrderDetailSerializer",
    "OrderListItemSerializer",
    "CreateOrderFromCartSerializer",
    "OrderTimelineSerializer",
    # Permissions
    "IsAuthenticated",
    "IsOrderOwner",
    "IsInternalService",
    "IsAdminOrStaff",
]
