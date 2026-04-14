"""
Domain layer for Order context.

Exports all domain concepts for use in other layers.
"""

from .entities import Order, OrderItem
from .enums import (
    OrderStatus, PaymentStatus, FulfillmentStatus, OrderEventType, Currency
)
from .value_objects import (
    Money, OrderNumber, ProductReference, AddressSnapshot, CustomerSnapshot,
    ProductSnapshot, ItemLinePrice, OrderTotals, ReservationReference
)
from .repositories import OrderRepository, OrderItemRepository
from .services import (
    OrderNumberGenerator, OrderValidator, OrderStateTransitionService,
    OrderCalculationService
)

__all__ = [
    # Entities
    "Order",
    "OrderItem",
    # Enums
    "OrderStatus",
    "PaymentStatus",
    "FulfillmentStatus",
    "OrderEventType",
    "Currency",
    # Value Objects
    "Money",
    "OrderNumber",
    "ProductReference",
    "AddressSnapshot",
    "CustomerSnapshot",
    "ProductSnapshot",
    "ItemLinePrice",
    "OrderTotals",
    "ReservationReference",
    # Repositories
    "OrderRepository",
    "OrderItemRepository",
    # Services
    "OrderNumberGenerator",
    "OrderValidator",
    "OrderStateTransitionService",
    "OrderCalculationService",
]
