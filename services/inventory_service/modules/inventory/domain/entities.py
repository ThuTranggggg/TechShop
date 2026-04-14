"""
Domain entities for Inventory context.

Core business logic and rules for StockItem, StockReservation, and StockMovement.
"""
from typing import Optional
from datetime import datetime, timedelta
from uuid import UUID

from .enums import ReservationStatus, StockMovementType
from .value_objects import ProductReference, StockStatus, Quantity


class StockItem:
    """
    StockItem aggregate root.
    
    Represents the inventory of a product/variant at a specific warehouse.
    Enforces business rules around stock levels and availability.
    """
    
    def __init__(
        self,
        id: UUID,
        product_reference: ProductReference,
        warehouse_code: str,
        on_hand_quantity: int,
        reserved_quantity: int = 0,
        safety_stock: int = 0,
        is_active: bool = True,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.product_reference = product_reference
        self.warehouse_code = warehouse_code
        self.safety_stock = safety_stock
        self.is_active = is_active
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        
        # Validate stock status
        self._status = StockStatus(on_hand_quantity, reserved_quantity)
    
    @property
    def on_hand_quantity(self) -> int:
        return self._status.on_hand_quantity
    
    @property
    def reserved_quantity(self) -> int:
        return self._status.reserved_quantity
    
    @property
    def available_quantity(self) -> int:
        return self._status.available_quantity
    
    @property
    def product_id(self) -> str:
        return self.product_reference.product_id
    
    @property
    def variant_id(self) -> Optional[str]:
        return self.product_reference.variant_id
    
    @property
    def sku(self) -> Optional[str]:
        return self.product_reference.sku
    
    def is_in_stock(self) -> bool:
        """Check if item is in stock (available quantity > 0)."""
        return self.available_quantity > 0
    
    def is_low_stock(self) -> bool:
        """Check if item is low stock (on_hand <= safety_stock)."""
        return self.on_hand_quantity <= self.safety_stock
    
    def can_reserve(self, quantity: int) -> bool:
        """Check if we can reserve the given quantity."""
        return self._status.can_reserve(quantity)
    
    def receive_stock(self, quantity: int, reason: str = "manual_stock_in"):
        """Increase on-hand quantity."""
        if quantity <= 0:
            raise ValueError("Stock in quantity must be positive")
        
        new_status = StockStatus(
            on_hand_quantity=self.on_hand_quantity + quantity,
            reserved_quantity=self.reserved_quantity,
        )
        self._status = new_status
        self.updated_at = datetime.utcnow()
    
    def adjust_stock(self, quantity: int, reason: str = "manual_adjustment"):
        """
        Adjust stock level.
        
        Can be positive (increase) or negative (decrease).
        Both on_hand and available are affected.
        """
        new_on_hand = self.on_hand_quantity + quantity
        
        if new_on_hand < 0:
            raise ValueError(
                f"Adjustment would result in negative on_hand. "
                f"Current: {self.on_hand_quantity}, Adjustment: {quantity}"
            )
        
        new_status = StockStatus(
            on_hand_quantity=new_on_hand,
            reserved_quantity=self.reserved_quantity,
        )
        self._status = new_status
        self.updated_at = datetime.utcnow()
    
    def create_reservation(self, quantity: int) -> "StockReservation":
        """Create a reservation for the given quantity."""
        if not self.can_reserve(quantity):
            raise ValueError(
                f"Cannot reserve {quantity}. Available: {self.available_quantity}"
            )
        
        # Update status
        new_status = self._status.reserve(quantity)
        self._status = new_status
        self.updated_at = datetime.utcnow()
        
        # Create reservation entity
        return StockReservation(
            id=None,  # Will be assigned by infrastructure
            stock_item_id=self.id,
            product_reference=self.product_reference,
            quantity=quantity,
            status=ReservationStatus.ACTIVE,
        )
    
    def confirm_reservation(self, quantity: int):
        """Confirm a reservation (deduct from on-hand)."""
        new_status = self._status.confirm_reservation(quantity)
        self._status = new_status
        self.updated_at = datetime.utcnow()
    
    def release_reservation(self, quantity: int):
        """Release a reservation (return to available)."""
        new_status = self._status.release_reservation(quantity)
        self._status = new_status
        self.updated_at = datetime.utcnow()
    
    def deactivate(self):
        """Deactivate this stock item."""
        self.is_active = False
        self.updated_at = datetime.utcnow()
    
    def activate(self):
        """Activate this stock item."""
        self.is_active = True
        self.updated_at = datetime.utcnow()


class StockReservation:
    """
    StockReservation entity.
    
    Represents a temporary reservation of stock for a cart/order.
    Has a defined lifecycle: active -> confirmed/released/cancelled/expired.
    """
    
    def __init__(
        self,
        id: UUID,
        stock_item_id: UUID,
        product_reference: ProductReference,
        quantity: int,
        status: ReservationStatus = ReservationStatus.ACTIVE,
        order_id: Optional[str] = None,
        cart_id: Optional[str] = None,
        user_id: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        metadata: Optional[dict] = None,
    ):
        self.id = id
        self.stock_item_id = stock_item_id
        self.product_reference = product_reference
        self.quantity = quantity
        self.status = status
        self.order_id = order_id
        self.cart_id = cart_id
        self.user_id = user_id
        self.expires_at = expires_at or (datetime.utcnow() + timedelta(hours=1))
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.metadata = metadata or {}
    
    @property
    def product_id(self) -> str:
        return self.product_reference.product_id
    
    @property
    def variant_id(self) -> Optional[str]:
        return self.product_reference.variant_id
    
    @property
    def sku(self) -> Optional[str]:
        return self.product_reference.sku
    
    def is_expired(self) -> bool:
        """Check if reservation has expired."""
        return datetime.utcnow() > self.expires_at
    
    def is_active(self) -> bool:
        """Check if reservation is active (not expired and status is ACTIVE)."""
        return self.status == ReservationStatus.ACTIVE and not self.is_expired()
    
    def can_confirm(self) -> bool:
        """Check if reservation can be confirmed."""
        return self.status == ReservationStatus.ACTIVE and not self.is_expired()
    
    def can_release(self) -> bool:
        """Check if reservation can be released."""
        return self.status == ReservationStatus.ACTIVE
    
    def confirm(self):
        """Confirm the reservation."""
        if not self.can_confirm():
            raise ValueError(
                f"Cannot confirm reservation. Status: {self.status}, "
                f"Expired: {self.is_expired()}"
            )
        self.status = ReservationStatus.CONFIRMED
        self.updated_at = datetime.utcnow()
    
    def release(self):
        """Release the reservation."""
        if not self.can_release():
            raise ValueError(f"Cannot release reservation. Status: {self.status}")
        self.status = ReservationStatus.RELEASED
        self.updated_at = datetime.utcnow()
    
    def cancel(self):
        """Cancel the reservation."""
        self.status = ReservationStatus.CANCELLED
        self.updated_at = datetime.utcnow()
    
    def expire(self):
        """Mark reservation as expired."""
        self.status = ReservationStatus.EXPIRED
        self.updated_at = datetime.utcnow()
    
    def extend_expiry(self, minutes: int = 60):
        """Extend the expiration time."""
        if self.status != ReservationStatus.ACTIVE:
            raise ValueError(
                f"Cannot extend expiry for non-active reservation. Status: {self.status}"
            )
        self.expires_at = datetime.utcnow() + timedelta(minutes=minutes)
        self.updated_at = datetime.utcnow()


class StockMovement:
    """
    StockMovement entity.
    
    Represents a historical record of stock changes.
    Used for audit trail and inventory reconciliation.
    """
    
    def __init__(
        self,
        id: UUID,
        stock_item_id: UUID,
        product_reference: ProductReference,
        movement_type: StockMovementType,
        quantity: int,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
        note: Optional[str] = None,
        created_by: Optional[str] = None,
        created_at: Optional[datetime] = None,
        metadata: Optional[dict] = None,
    ):
        self.id = id
        self.stock_item_id = stock_item_id
        self.product_reference = product_reference
        self.movement_type = movement_type
        self.quantity = quantity
        self.reference_type = reference_type
        self.reference_id = reference_id
        self.note = note
        self.created_by = created_by
        self.created_at = created_at or datetime.utcnow()
        self.metadata = metadata or {}
    
    @property
    def product_id(self) -> str:
        return self.product_reference.product_id
    
    @property
    def variant_id(self) -> Optional[str]:
        return self.product_reference.variant_id
    
    @property
    def sku(self) -> Optional[str]:
        return self.product_reference.sku
