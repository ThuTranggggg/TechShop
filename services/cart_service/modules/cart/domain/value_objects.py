"""
Value objects for Cart domain context.

Value objects are immutable and have no identity beyond their values.
"""
from typing import Optional, Dict, Any
from decimal import Decimal


class Quantity:
    """
    Value object representing a positive quantity.
    
    Ensures quantity is always > 0.
    """
    
    def __init__(self, value: int):
        if not isinstance(value, int):
            raise ValueError(f"Quantity must be an integer, got {type(value)}")
        if value <= 0:
            raise ValueError(f"Quantity must be greater than 0, got {value}")
        self._value = value
    
    @property
    def value(self) -> int:
        return self._value
    
    def increase(self, increment: int) -> "Quantity":
        """Return new Quantity with increased value."""
        if increment <= 0:
            raise ValueError(f"Increment must be > 0, got {increment}")
        return Quantity(self._value + increment)
    
    def decrease(self, decrement: int) -> "Quantity":
        """Return new Quantity with decreased value."""
        if decrement <= 0:
            raise ValueError(f"Decrement must be > 0, got {decrement}")
        new_value = self._value - decrement
        if new_value <= 0:
            raise ValueError(
                f"Cannot decrease quantity by {decrement}. Would result in {new_value}"
            )
        return Quantity(new_value)
    
    def __eq__(self, other):
        if isinstance(other, Quantity):
            return self._value == other._value
        return False
    
    def __lt__(self, other):
        if isinstance(other, Quantity):
            return self._value < other._value
        if isinstance(other, int):
            return self._value < other
        raise TypeError(f"Cannot compare Quantity with {type(other)}")
    
    def __le__(self, other):
        if isinstance(other, Quantity):
            return self._value <= other._value
        if isinstance(other, int):
            return self._value <= other
        return False
    
    def __gt__(self, other):
        if isinstance(other, Quantity):
            return self._value > other._value
        if isinstance(other, int):
            return self._value > other
        return False
    
    def __ge__(self, other):
        if isinstance(other, Quantity):
            return self._value >= other._value
        if isinstance(other, int):
            return self._value >= other
        return False
    
    def __repr__(self):
        return f"Quantity({self._value})"


class ProductReference:
    """
    Value object representing a reference to a product.
    
    Cart does not own product domain; this captures required info only.
    """
    
    def __init__(self, product_id: str, variant_id: Optional[str] = None):
        if not product_id or not isinstance(product_id, str):
            raise ValueError("product_id is required and must be a string")
        self.product_id = product_id
        self.variant_id = variant_id
    
    def __eq__(self, other):
        if isinstance(other, ProductReference):
            return (
                self.product_id == other.product_id
                and self.variant_id == other.variant_id
            )
        return False
    
    def __hash__(self):
        return hash((self.product_id, self.variant_id))
    
    def __repr__(self):
        return f"ProductReference(product={self.product_id}, variant={self.variant_id})"


class Price:
    """
    Value object representing a price snapshot.
    
    Captures price at time of cart item addition for display stability.
    """
    
    def __init__(self, amount: Decimal, currency: str = "USD"):
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        if amount < 0:
            raise ValueError(f"Price cannot be negative, got {amount}")
        self.amount = amount
        self.currency = currency
    
    def line_total(self, quantity: Quantity) -> "Price":
        """Calculate line total: price * quantity."""
        total = self.amount * quantity.value
        return Price(total, self.currency)
    
    def __eq__(self, other):
        if isinstance(other, Price):
            return self.amount == other.amount and self.currency == other.currency
        return False
    
    def __repr__(self):
        return f"Price({self.amount} {self.currency})"


class ProductSnapshot:
    """
    Value object capturing product info needed for stable cart display.
    
    This is the minimal snapshot to avoid stale product data in cart UI.
    Full product details should be fetched from product_service.
    """
    
    def __init__(
        self,
        product_id: str,
        name: str,
        slug: str,
        sku: Optional[str] = None,
        brand_name: Optional[str] = None,
        category_name: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        variant_id: Optional[str] = None,
        variant_name: Optional[str] = None,
        attributes_snapshot: Optional[Dict[str, Any]] = None,
    ):
        self.product_id = product_id
        self.name = name
        self.slug = slug
        self.sku = sku
        self.brand_name = brand_name
        self.category_name = category_name
        self.thumbnail_url = thumbnail_url
        self.variant_id = variant_id
        self.variant_name = variant_name
        self.attributes_snapshot = attributes_snapshot or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "product_id": self.product_id,
            "name": self.name,
            "slug": self.slug,
            "sku": self.sku,
            "brand_name": self.brand_name,
            "category_name": self.category_name,
            "thumbnail_url": self.thumbnail_url,
            "variant_id": self.variant_id,
            "variant_name": self.variant_name,
            "attributes": self.attributes_snapshot,
        }
    
    def __repr__(self):
        return f"ProductSnapshot(product={self.product_id}, variant={self.variant_id})"
