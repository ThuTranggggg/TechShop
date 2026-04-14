"""
Domain value objects for Inventory context.

Immutable objects that represent concepts in the domain.
"""
from dataclasses import dataclass
from typing import Optional
from decimal import Decimal


@dataclass(frozen=True)
class Quantity:
    """
    Value object representing a quantity.
    
    Ensures quantity is never negative and enforces domain rules.
    """
    value: int
    
    def __post_init__(self):
        if self.value < 0:
            raise ValueError("Quantity cannot be negative")
    
    def __add__(self, other: "Quantity") -> "Quantity":
        return Quantity(self.value + other.value)
    
    def __sub__(self, other: "Quantity") -> "Quantity":
        return Quantity(self.value - other.value)
    
    def __le__(self, other: "Quantity") -> bool:
        return self.value <= other.value
    
    def __ge__(self, other: "Quantity") -> bool:
        return self.value >= other.value
    
    def __lt__(self, other: "Quantity") -> bool:
        return self.value < other.value
    
    def __gt__(self, other: "Quantity") -> bool:
        return self.value > other.value
    
    def __eq__(self, other: "Quantity") -> bool:
        return self.value == other.value


@dataclass(frozen=True)
class ProductReference:
    """
    Value object representing a reference to a product from product_service.
    
    Does not embed full product data - only references the product.
    """
    product_id: str  # UUID from product_service
    variant_id: Optional[str] = None  # UUID nullable
    sku: Optional[str] = None  # SKU from product


class StockStatus:
    """
    Value object representing the stock status at a point in time.
    """
    
    def __init__(
        self,
        on_hand_quantity: int,
        reserved_quantity: int,
    ):
        if on_hand_quantity < 0:
            raise ValueError("on_hand_quantity cannot be negative")
        if reserved_quantity < 0:
            raise ValueError("reserved_quantity cannot be negative")
        if reserved_quantity > on_hand_quantity:
            raise ValueError("reserved_quantity cannot exceed on_hand_quantity")
        
        self.on_hand_quantity = on_hand_quantity
        self.reserved_quantity = reserved_quantity
    
    @property
    def available_quantity(self) -> int:
        """Calculate available quantity (on-hand - reserved)."""
        return self.on_hand_quantity - self.reserved_quantity
    
    def can_reserve(self, quantity: int) -> bool:
        """Check if we can reserve the given quantity."""
        return self.available_quantity >= quantity
    
    def reserve(self, quantity: int) -> "StockStatus":
        """Create new status after reservation."""
        if not self.can_reserve(quantity):
            raise ValueError(
                f"Cannot reserve {quantity}. Available: {self.available_quantity}"
            )
        return StockStatus(
            on_hand_quantity=self.on_hand_quantity,
            reserved_quantity=self.reserved_quantity + quantity,
        )
    
    def release_reservation(self, quantity: int) -> "StockStatus":
        """Create new status after releasing reservation."""
        new_reserved = self.reserved_quantity - quantity
        if new_reserved < 0:
            raise ValueError(
                f"Cannot release {quantity}. Reserved: {self.reserved_quantity}"
            )
        return StockStatus(
            on_hand_quantity=self.on_hand_quantity,
            reserved_quantity=new_reserved,
        )
    
    def confirm_reservation(self, quantity: int) -> "StockStatus":
        """Create new status after confirming reservation (deducting from on-hand)."""
        if self.reserved_quantity < quantity:
            raise ValueError(
                f"Cannot confirm {quantity}. Reserved: {self.reserved_quantity}"
            )
        return StockStatus(
            on_hand_quantity=self.on_hand_quantity - quantity,
            reserved_quantity=self.reserved_quantity - quantity,
        )
    
    def __eq__(self, other):
        if not isinstance(other, StockStatus):
            return False
        return (
            self.on_hand_quantity == other.on_hand_quantity
            and self.reserved_quantity == other.reserved_quantity
        )
