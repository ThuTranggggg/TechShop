"""
Domain value objects for Order context.

Immutable types representing composite values within the order domain.
"""

from typing import Optional, Dict, Any
from decimal import Decimal
from uuid import UUID
from dataclasses import dataclass
from datetime import datetime

from .enums import Currency


@dataclass(frozen=True)
class Money:
    """
    Value object representing an amount of money in a specific currency.
    """
    
    amount: Decimal
    currency: Currency
    
    def __post_init__(self):
        if self.amount < 0:
            raise ValueError(f"Money amount cannot be negative: {self.amount}")
    
    def add(self, other: "Money") -> "Money":
        """Add two money objects (must have same currency)."""
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)
    
    def multiply(self, multiplier: int | float) -> "Money":
        """Multiply money by a scalar."""
        return Money(self.amount * Decimal(str(multiplier)), self.currency)
    
    def __str__(self):
        return f"{self.amount:.2f} {self.currency}"
    
    def __repr__(self):
        return f"Money({self.amount}, {self.currency})"


@dataclass(frozen=True)
class OrderNumber:
    """
    Value object representing a human-readable order number.
    
    Format: ORD-YYYYMMDD-XXXXXX (e.g., ORD-20260411-000123)
    """
    
    value: str
    
    def __post_init__(self):
        if not self.value.startswith("ORD-"):
            raise ValueError(f"Order number must start with 'ORD-': {self.value}")
    
    def __str__(self):
        return self.value
    
    def __repr__(self):
        return f"OrderNumber({self.value})"


@dataclass(frozen=True)
class ProductReference:
    """
    Value object representing a reference to a product.
    
    Used in OrderItem to maintain referential integrity without full product entity.
    """
    
    product_id: UUID
    variant_id: Optional[UUID] = None
    sku: Optional[str] = None
    
    def __repr__(self):
        return f"ProductReference(id={self.product_id}, variant={self.variant_id}, sku={self.sku})"


@dataclass(frozen=True)
class AddressSnapshot:
    """
    Value object representing a shipping address snapshot.
    
    Immutable snapshot of address at time of order creation.
    """
    
    receiver_name: str
    receiver_phone: str
    line1: str
    line2: Optional[str] = None
    ward: Optional[str] = None
    district: str = ""
    city: str = ""
    country: str = ""
    postal_code: Optional[str] = None
    
    def __post_init__(self):
        if not self.receiver_name.strip():
            raise ValueError("Receiver name is required")
        if not self.receiver_phone.strip():
            raise ValueError("Receiver phone is required")
        if not self.line1.strip():
            raise ValueError("Line1 is required")
    
    def __repr__(self):
        return f"AddressSnapshot({self.receiver_name}, {self.city})"


@dataclass(frozen=True)
class CustomerSnapshot:
    """
    Value object representing a customer snapshot.
    
    Immutable snapshot of customer info at time of order creation.
    """
    
    name: str
    email: str
    phone: Optional[str] = None
    user_id: Optional[UUID] = None
    
    def __post_init__(self):
        if not self.name.strip():
            raise ValueError("Customer name is required")
        if not self.email.strip():
            raise ValueError("Customer email is required")
    
    def __repr__(self):
        return f"CustomerSnapshot({self.name}, {self.email})"


@dataclass(frozen=True)
class ProductSnapshot:
    """
    Value object representing a product snapshot in an order item.
    
    Immutable snapshot of product details at time of purchase.
    Used to preserve product info in order history even if product changes.
    """
    
    product_id: UUID
    name: str
    slug: str
    thumbnail_url: Optional[str] = None
    brand_name: Optional[str] = None
    category_name: Optional[str] = None
    variant_name: Optional[str] = None
    sku: Optional[str] = None
    attributes: Dict[str, Any] = None
    
    def __post_init__(self):
        if not self.name.strip():
            raise ValueError("Product name is required")
        if not self.slug.strip():
            raise ValueError("Product slug is required")
        # Allow None, convert to empty dict if needed
        if self.attributes is None:
            object.__setattr__(self, 'attributes', {})
        elif not isinstance(self.attributes, dict):
            raise ValueError("Attributes must be a dict")
    
    def __repr__(self):
        return f"ProductSnapshot({self.name})"


@dataclass(frozen=True)
class ItemLinePrice:
    """
    Value object representing pricing for an order line item.
    """
    
    unit_price: Money
    quantity: int
    currency: Currency
    
    def __post_init__(self):
        if self.quantity <= 0:
            raise ValueError(f"Quantity must be > 0, got {self.quantity}")
        if self.unit_price.currency != self.currency:
            raise ValueError("Unit price currency must match line currency")
    
    @property
    def line_total(self) -> Money:
        """Calculate line total: unit_price * quantity."""
        return self.unit_price.multiply(self.quantity)
    
    def __repr__(self):
        return f"ItemLinePrice({self.unit_price}, qty={self.quantity})"


@dataclass(frozen=True)
class OrderTotals:
    """
    Value object representing all totals for an order.
    """
    
    subtotal: Money
    shipping_fee: Money
    discount: Money
    tax: Money
    grand_total: Money
    currency: Currency
    
    def __post_init__(self):
        # Validate all have same currency
        for money_obj in [self.subtotal, self.shipping_fee, self.discount, self.tax, self.grand_total]:
            if money_obj.currency != self.currency:
                raise ValueError(f"All amounts must use {self.currency}")
        
        # Validate grand_total calculation
        expected_total = self.subtotal.add(self.shipping_fee).add(self.tax)
        expected_total = Money(
            expected_total.amount - self.discount.amount,
            self.currency
        )
        if expected_total.amount != self.grand_total.amount:
            raise ValueError(
                f"Grand total mismatch. Expected {expected_total}, got {self.grand_total}"
            )
    
    def __repr__(self):
        return f"OrderTotals(subtotal={self.subtotal}, total={self.grand_total})"


@dataclass(frozen=True)
class ReservationReference:
    """
    Value object representing a stock reservation reference.
    """
    
    reservation_id: str
    product_id: UUID
    quantity: int
    expires_at: Optional[datetime] = None
    
    def __repr__(self):
        return f"ReservationReference(id={self.reservation_id}, product={self.product_id})"
