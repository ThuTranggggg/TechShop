"""
Infrastructure layer for Order context.

Contains ORM models, repository implementations, and inter-service clients.
"""

from .models import OrderModel, OrderItemModel, OrderStatusHistoryModel
from .repositories import OrderRepositoryImpl, OrderItemRepositoryImpl
from .clients import (
    CartServiceClient, ProductServiceClient, InventoryServiceClient, PaymentServiceClient,
    ShippingServiceClient
)

__all__ = [
    # Models
    "OrderModel",
    "OrderItemModel",
    "OrderStatusHistoryModel",
    # Repositories
    "OrderRepositoryImpl",
    "OrderItemRepositoryImpl",
    # Clients
    "CartServiceClient",
    "ProductServiceClient",
    "InventoryServiceClient",
    "PaymentServiceClient",
    "ShippingServiceClient",
]
