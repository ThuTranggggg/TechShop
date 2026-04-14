"""
Enums for Cart domain context.
"""
from enum import Enum


class CartStatus(str, Enum):
    """Status of a shopping cart."""
    ACTIVE = "active"
    CHECKED_OUT = "checked_out"
    ABANDONED = "abandoned"
    EXPIRED = "expired"
    MERGED = "merged"


class CartItemStatus(str, Enum):
    """Status of an item in the cart."""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    PRODUCT_INACTIVE = "product_inactive"
    VARIANT_NOT_FOUND = "variant_not_found"
