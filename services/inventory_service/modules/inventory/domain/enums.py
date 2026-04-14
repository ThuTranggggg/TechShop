"""
Domain enums for Inventory context.

Defines status values and enumerations for inventory operations.
"""
from enum import Enum


class ReservationStatus(str, Enum):
    """Status of a stock reservation."""
    ACTIVE = "active"
    CONFIRMED = "confirmed"
    RELEASED = "released"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class StockMovementType(str, Enum):
    """Type of stock movement."""
    STOCK_IN = "stock_in"
    STOCK_OUT = "stock_out"
    RESERVATION_CREATED = "reservation_created"
    RESERVATION_RELEASED = "reservation_released"
    RESERVATION_CONFIRMED = "reservation_confirmed"
    ADJUSTMENT_INCREASE = "adjustment_increase"
    ADJUSTMENT_DECREASE = "adjustment_decrease"
    CORRECTION = "correction"


class WarehouseType(str, Enum):
    """Type of warehouse location."""
    MAIN = "main"
    BRANCH = "branch"
    THIRD_PARTY = "third_party"
    HOLDING = "holding"
