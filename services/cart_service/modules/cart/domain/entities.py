"""
Domain entities for Cart context.

Core business logic and rules for Cart and CartItem.
"""
from typing import Optional, Dict, List, Any
from datetime import datetime
from uuid import UUID

from .enums import CartStatus, CartItemStatus
from .value_objects import Quantity, ProductReference, Price, ProductSnapshot


class CartItem:
    """
    CartItem entity.
    
    Represents a product in a user's cart with quantity and snapshot.
    """
    
    def __init__(
        self,
        id: UUID,
        cart_id: UUID,
        product_reference: ProductReference,
        quantity: Quantity,
        price_snapshot: Price,
        product_snapshot: ProductSnapshot,
        status: CartItemStatus = CartItemStatus.AVAILABLE,
        availability_checked_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.cart_id = cart_id
        self.product_reference = product_reference
        self.quantity = quantity
        self.price_snapshot = price_snapshot
        self.product_snapshot = product_snapshot
        self.status = status
        self.availability_checked_at = availability_checked_at
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
    
    def update_quantity(self, new_quantity: Quantity) -> None:
        """Update quantity and mark as modified."""
        if new_quantity.value <= 0:
            raise ValueError("Quantity must be greater than 0")
        self.quantity = new_quantity
        self.updated_at = datetime.utcnow()
    
    def increase_quantity(self, increment: int) -> None:
        """Increase quantity by increment."""
        new_quantity = self.quantity.increase(increment)
        self.update_quantity(new_quantity)
    
    def decrease_quantity(self, decrement: int) -> None:
        """Decrease quantity by decrement."""
        new_quantity = self.quantity.decrease(decrement)
        self.update_quantity(new_quantity)
    
    def set_unavailable(self, reason: CartItemStatus = CartItemStatus.OUT_OF_STOCK) -> None:
        """Mark item as unavailable."""
        self.status = reason
        self.updated_at = datetime.utcnow()
    
    def set_available(self) -> None:
        """Mark item as available."""
        self.status = CartItemStatus.AVAILABLE
        self.updated_at = datetime.utcnow()
    
    def update_snapshot(
        self,
        product_snapshot: Optional[ProductSnapshot] = None,
        price_snapshot: Optional[Price] = None,
    ) -> None:
        """Update product and/or price snapshot."""
        if product_snapshot:
            self.product_snapshot = product_snapshot
        if price_snapshot:
            self.price_snapshot = price_snapshot
        self.updated_at = datetime.utcnow()
    
    def calculate_line_total(self) -> Price:
        """Calculate line total: price * quantity."""
        return self.price_snapshot.line_total(self.quantity)
    
    def is_valid(self) -> bool:
        """Check if item is in a valid state for checkout."""
        return self.status == CartItemStatus.AVAILABLE
    
    def __repr__(self):
        return f"CartItem({self.product_reference}, qty={self.quantity.value})"


class Cart:
    """
    Cart aggregate root.
    
    Represents a user's shopping cart.
    
    Business Rules:
    - Each user can have only one active cart
    - Cart can only be checked out once (immutable after checkout)
    - Active cart is the only one the user can modify
    """
    
    def __init__(
        self,
        id: UUID,
        user_id: UUID,
        status: CartStatus = CartStatus.ACTIVE,
        currency: str = "USD",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.user_id = user_id
        self.status = status
        self.currency = currency
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self._items: Dict[str, CartItem] = {}  # Key: "{product_id}#{variant_id or ''}"
    
    @property
    def items(self) -> List[CartItem]:
        """Get all items in cart."""
        return list(self._items.values())
    
    @property
    def item_count(self) -> int:
        """Total number of unique items."""
        return len(self._items)
    
    @property
    def total_quantity(self) -> int:
        """Total quantity across all items."""
        return sum(item.quantity.value for item in self._items.values())
    
    @property
    def subtotal_amount(self) -> float:
        """Calculate subtotal before tax/shipping."""
        total = sum(
            float(item.calculate_line_total().amount)
            for item in self._items.values()
        )
        return total
    
    @property
    def last_activity_at(self) -> datetime:
        """Last time cart was modified."""
        return self.updated_at
    
    def _get_item_key(self, product_reference: ProductReference) -> str:
        """Generate unique key for product+variant combination."""
        return f"{product_reference.product_id}#{product_reference.variant_id or ''}"
    
    def can_modify(self) -> bool:
        """Check if cart can be modified."""
        return self.status == CartStatus.ACTIVE
    
    def add_item(
        self,
        item_id: UUID,
        product_reference: ProductReference,
        quantity: Quantity,
        price_snapshot: Price,
        product_snapshot: ProductSnapshot,
    ) -> CartItem:
        """
        Add or update item in cart.
        
        If item with same product+variant exists, increases quantity instead.
        """
        if not self.can_modify():
            raise RuntimeError(f"Cannot modify cart with status {self.status}")
        
        key = self._get_item_key(product_reference)
        
        if key in self._items:
            # Item already in cart - increase quantity
            existing_item = self._items[key]
            existing_item.increase_quantity(quantity.value)
            return existing_item
        else:
            # New item - create it
            new_item = CartItem(
                id=item_id,
                cart_id=self.id,
                product_reference=product_reference,
                quantity=quantity,
                price_snapshot=price_snapshot,
                product_snapshot=product_snapshot,
            )
            self._items[key] = new_item
            self.updated_at = datetime.utcnow()
            return new_item
    
    def get_item(self, item_id: UUID) -> Optional[CartItem]:
        """Get item by ID."""
        for item in self._items.values():
            if item.id == item_id:
                return item
        return None
    
    def get_item_by_product(self, product_reference: ProductReference) -> Optional[CartItem]:
        """Get item by product reference."""
        key = self._get_item_key(product_reference)
        return self._items.get(key)
    
    def remove_item(self, item_id: UUID) -> None:
        """Remove item from cart by ID."""
        if not self.can_modify():
            raise RuntimeError(f"Cannot modify cart with status {self.status}")
        
        for key, item in list(self._items.items()):
            if item.id == item_id:
                del self._items[key]
                self.updated_at = datetime.utcnow()
                return
        
        raise ValueError(f"CartItem {item_id} not found in cart")
    
    def update_item_quantity(self, item_id: UUID, new_quantity: Quantity) -> CartItem:
        """Update quantity of an item."""
        if not self.can_modify():
            raise RuntimeError(f"Cannot modify cart with status {self.status}")
        
        item = self.get_item(item_id)
        if not item:
            raise ValueError(f"CartItem {item_id} not found in cart")
        
        item.update_quantity(new_quantity)
        self.updated_at = datetime.utcnow()
        return item
    
    def clear(self) -> None:
        """Remove all items from cart."""
        if not self.can_modify():
            raise RuntimeError(f"Cannot modify cart with status {self.status}")
        
        self._items.clear()
        self.updated_at = datetime.utcnow()
    
    def mark_checked_out(self) -> None:
        """Mark cart as checked out (immutable after this)."""
        if self.status != CartStatus.ACTIVE:
            raise RuntimeError(
                f"Can only checkout active carts, current status: {self.status}"
            )
        self.status = CartStatus.CHECKED_OUT
        self.updated_at = datetime.utcnow()
    
    def mark_abandoned(self) -> None:
        """Mark cart as abandoned."""
        self.status = CartStatus.ABANDONED
        self.updated_at = datetime.utcnow()
    
    def is_empty(self) -> bool:
        """Check if cart has no items."""
        return len(self._items) == 0
    
    def validate(self) -> tuple[bool, List[Dict[str, Any]]]:
        """
        Validate all items in cart.
        
        Returns: (is_valid, list of issues)
        """
        issues = []
        
        for item in self._items.values():
            if not item.is_valid():
                issues.append({
                    "item_id": str(item.id),
                    "product_id": item.product_reference.product_id,
                    "status": item.status.value,
                    "message": f"Item is {item.status.value}",
                })
        
        return len(issues) == 0, issues
    
    def __repr__(self):
        return f"Cart(user={self.user_id}, items={self.item_count}, status={self.status})"
