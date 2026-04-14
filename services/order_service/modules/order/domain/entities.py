"""
Domain entities for Order context.

Core business logic for Order and OrderItem aggregates.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from .enums import OrderStatus, PaymentStatus, FulfillmentStatus, Currency
from .value_objects import (
    Money, OrderNumber, ProductReference, AddressSnapshot, CustomerSnapshot,
    ProductSnapshot, ItemLinePrice, OrderTotals, ReservationReference
)


class OrderItem:
    """
    Order item entity.
    
    Represents a snapshot of a line item in an order.
    This is immutable after creation to preserve order history integrity.
    """
    
    def __init__(
        self,
        id: UUID,
        order_id: UUID,
        product_reference: ProductReference,
        product_snapshot: ProductSnapshot,
        quantity: int,
        unit_price: Money,
        currency: Currency,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.order_id = order_id
        self.product_reference = product_reference
        self.product_snapshot = product_snapshot
        self.quantity = quantity
        self.unit_price = unit_price
        self.currency = currency
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        
        # Validate
        if self.quantity <= 0:
            raise ValueError("Order item quantity must be > 0")
        if self.unit_price.currency != self.currency:
            raise ValueError("Unit price currency must match order currency")
    
    @property
    def line_total(self) -> Money:
        """Calculate line total: unit_price * quantity."""
        return self.unit_price.multiply(self.quantity)
    
    def __repr__(self):
        return f"OrderItem({self.product_snapshot.name}, qty={self.quantity})"


class Order:
    """
    Order aggregate root.
    
    Represents a customer order with all line items, prices, and state.
    Implements business logic for order lifecycle and state transitions.
    """
    
    def __init__(
        self,
        id: UUID,
        order_number: OrderNumber,
        user_id: UUID,
        cart_id: Optional[UUID],
        currency: Currency,
        customer_snapshot: CustomerSnapshot,
        address_snapshot: AddressSnapshot,
        status: OrderStatus = OrderStatus.PENDING,
        payment_status: PaymentStatus = PaymentStatus.UNPAID,
        fulfillment_status: FulfillmentStatus = FulfillmentStatus.UNFULFILLED,
        items: Optional[List[OrderItem]] = None,
        subtotal: Optional[Money] = None,
        shipping_fee: Optional[Money] = None,
        discount: Optional[Money] = None,
        tax: Optional[Money] = None,
        grand_total: Optional[Money] = None,
        total_quantity: int = 0,
        item_count: int = 0,
        notes: Optional[str] = None,
        payment_id: Optional[UUID] = None,
        payment_reference: Optional[str] = None,
        shipment_id: Optional[UUID] = None,
        shipment_reference: Optional[str] = None,
        stock_reservation_refs: Optional[List[Dict[str, Any]]] = None,
        placed_at: Optional[datetime] = None,
        paid_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.order_number = order_number
        self.user_id = user_id
        self.cart_id = cart_id
        self.currency = currency
        self.customer_snapshot = customer_snapshot
        self.address_snapshot = address_snapshot
        self.status = status
        self.payment_status = payment_status
        self.fulfillment_status = fulfillment_status
        self.items = items or []
        self.notes = notes or ""
        self.payment_id = payment_id
        self.payment_reference = payment_reference
        self.shipment_id = shipment_id
        self.shipment_reference = shipment_reference
        self.stock_reservation_refs = stock_reservation_refs or []
        
        # Milestones
        self.placed_at = placed_at
        self.paid_at = paid_at
        self.cancelled_at = cancelled_at
        self.completed_at = completed_at
        
        # Timestamps
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        
        # Calculate or use provided totals
        if subtotal is None or shipping_fee is None or tax is None or grand_total is None:
            self._calculate_totals()
        else:
            self.subtotal = subtotal
            self.shipping_fee = shipping_fee
            self.discount = discount or Money(Decimal("0"), self.currency)
            self.tax = tax
            self.grand_total = grand_total
        
        self.total_quantity = total_quantity or sum(item.quantity for item in self.items)
        self.item_count = item_count or len(self.items)
    
    def _calculate_totals(self) -> None:
        """Calculate totals from items."""
        if not self.items:
            zero = Money(Decimal("0"), self.currency)
            self.subtotal = zero
            self.shipping_fee = zero
            self.discount = zero
            self.tax = zero
            self.grand_total = zero
        else:
            subtotal_amount = sum(Decimal(str(item.line_total.amount)) for item in self.items)
            self.subtotal = Money(subtotal_amount, self.currency)
            self.shipping_fee = Money(Decimal("0"), self.currency)
            self.discount = Money(Decimal("0"), self.currency)
            self.tax = Money(Decimal("0"), self.currency)
            self.grand_total = self.subtotal
    
    def add_item(self, item: OrderItem) -> None:
        """Add item to order."""
        if item.order_id != self.id:
            raise ValueError("Item order_id does not match")
        self.items.append(item)
        self._recalculate_totals()
    
    def _recalculate_totals(self) -> None:
        """Recalculate totals from items."""
        self.total_quantity = sum(item.quantity for item in self.items)
        self.item_count = len(self.items)
        self._calculate_totals()
        self.updated_at = datetime.utcnow()
    
    def set_totals(
        self,
        subtotal: Money,
        shipping_fee: Money,
        discount: Money,
        tax: Money,
        grand_total: Money,
    ) -> None:
        """
        Set totals explicitly.
        
        Use when totals are calculated externally (e.g., with shipping/tax service).
        """
        # Validate
        expected_total = subtotal.add(shipping_fee).add(tax)
        expected_total = Money(
            expected_total.amount - discount.amount,
            self.currency
        )
        if expected_total.amount != grand_total.amount:
            raise ValueError(
                f"Total mismatch. Expected {expected_total}, got {grand_total}"
            )
        
        self.subtotal = subtotal
        self.shipping_fee = shipping_fee
        self.discount = discount
        self.tax = tax
        self.grand_total = grand_total
        self.updated_at = datetime.utcnow()
    
    @property
    def is_valid_for_checkout(self) -> bool:
        """Check if order is valid after creation, before payment."""
        return (
            self.status in [OrderStatus.PENDING, OrderStatus.AWAITING_PAYMENT]
            and len(self.items) > 0
            and self.total_quantity > 0
            and self.customer_snapshot is not None
            and self.address_snapshot is not None
        )
    
    def mark_awaiting_payment(self, payment_reference: Optional[str] = None) -> None:
        """Transition to awaiting_payment state after stock reservation."""
        if self.status not in [OrderStatus.PENDING]:
            raise ValueError(
                f"Cannot mark awaiting_payment from {self.status}"
            )
        self.status = OrderStatus.AWAITING_PAYMENT
        if payment_reference:
            self.payment_reference = payment_reference
        self.payment_status = PaymentStatus.PENDING
        self.updated_at = datetime.utcnow()
    
    def mark_payment_success(self) -> None:
        """Mark order as paid after payment success."""
        if self.status not in [OrderStatus.AWAITING_PAYMENT]:
            raise ValueError(
                f"Cannot mark payment success from {self.status}"
            )
        self.status = OrderStatus.PAID
        self.payment_status = PaymentStatus.PAID
        self.paid_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def mark_payment_failed(self) -> None:
        """Mark order as payment failed."""
        if self.status not in [OrderStatus.AWAITING_PAYMENT, OrderStatus.PENDING]:
            raise ValueError(
                f"Cannot mark payment failed from {self.status}"
            )
        self.status = OrderStatus.PAYMENT_FAILED
        self.payment_status = PaymentStatus.FAILED
        self.updated_at = datetime.utcnow()
    
    def mark_processing(self) -> None:
        """Transition to processing state."""
        if self.status not in [OrderStatus.PAID]:
            raise ValueError(
                f"Cannot mark processing from {self.status}"
            )
        self.status = OrderStatus.PROCESSING
        self.fulfillment_status = FulfillmentStatus.PREPARING
        self.updated_at = datetime.utcnow()
    
    def mark_shipping(self, shipment_reference: Optional[str] = None) -> None:
        """Transition to shipping state."""
        if self.status not in [OrderStatus.PROCESSING]:
            raise ValueError(
                f"Cannot mark shipping from {self.status}"
            )
        self.status = OrderStatus.SHIPPING
        self.fulfillment_status = FulfillmentStatus.SHIPPED
        if shipment_reference:
            self.shipment_reference = shipment_reference
        self.updated_at = datetime.utcnow()
    
    def mark_delivered(self) -> None:
        """Transition to delivered state."""
        if self.status not in [OrderStatus.SHIPPING]:
            raise ValueError(
                f"Cannot mark delivered from {self.status}"
            )
        self.status = OrderStatus.DELIVERED
        self.fulfillment_status = FulfillmentStatus.DELIVERED
        self.updated_at = datetime.utcnow()
    
    def mark_completed(self) -> None:
        """Complete the order."""
        if self.status not in [OrderStatus.DELIVERED]:
            raise ValueError(
                f"Cannot complete from {self.status}"
            )
        self.status = OrderStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def mark_cancelled(self) -> None:
        """Cancel the order."""
        # Can cancel from several states
        if self.status in [OrderStatus.COMPLETED, OrderStatus.DELIVERED, OrderStatus.SHIPPING]:
            # Cannot easily cancel from these states
            raise ValueError(
                f"Cannot cancel from {self.status} (shipping already started)"
            )
        
        self.status = OrderStatus.CANCELLED
        self.cancelled_at = datetime.utcnow()
        
        # Release stock reservation if still active
        if self.stock_reservation_refs:
            self.fulfillment_status = FulfillmentStatus.CANCELLED
        
        self.updated_at = datetime.utcnow()
    
    def set_payment_info(
        self,
        payment_id: UUID,
        payment_reference: str,
    ) -> None:
        """Set payment reference info."""
        self.payment_id = payment_id
        self.payment_reference = payment_reference
        self.updated_at = datetime.utcnow()
    
    def set_shipment_info(
        self,
        shipment_id: UUID,
        shipment_reference: str,
    ) -> None:
        """Set shipment reference info."""
        self.shipment_id = shipment_id
        self.shipment_reference = shipment_reference
        self.updated_at = datetime.utcnow()
    
    def add_stock_reservation_ref(self, ref: Dict[str, Any]) -> None:
        """Add a stock reservation reference."""
        self.stock_reservation_refs.append(ref)
        self.updated_at = datetime.utcnow()
    
    def clear_stock_reservations(self) -> None:
        """Clear all reservation references."""
        self.stock_reservation_refs = []
        self.updated_at = datetime.utcnow()
    
    def __repr__(self):
        return f"Order({self.order_number}, user={self.user_id}, status={self.status})"
