"""
Domain services for Order context.

Contains complex business logic that doesn't belong to a single entity.
"""

from typing import List, Dict, Any, Optional
from decimal import Decimal
from uuid import UUID
from datetime import datetime

from .entities import Order, OrderItem
from .enums import OrderStatus, PaymentStatus, FulfillmentStatus
from .value_objects import Money, OrderNumber, Currency
from .repositories import OrderRepository


class OrderNumberGenerator:
    """
    Service for generating unique order numbers.
    
    Format: ORD-YYYYMMDD-XXXXXX (e.g., ORD-20260411-000001)
    """
    
    @staticmethod
    def generate(sequence: int) -> OrderNumber:
        """Generate unique order number."""
        from datetime import datetime
        date_part = datetime.utcnow().strftime("%Y%m%d")
        sequence_part = str(sequence).zfill(6)
        order_number_str = f"ORD-{date_part}-{sequence_part}"
        return OrderNumber(order_number_str)


class OrderValidator:
    """
    Service for validating order state and transitions.
    """
    
    @staticmethod
    def validate_checkout_payload(payload: Dict[str, Any]) -> bool:
        """Validate checkout payload structure."""
        required_fields = [
            "user_id",
            "cart_id",
            "items",
        ]
        
        for field in required_fields:
            if field not in payload:
                raise ValueError(f"Missing required field: {field}")
        
        items = payload.get("items", [])
        if not items:
            raise ValueError("Cart must have at least one item")
        
        customer = payload.get("customer", {})
        if customer and (not customer.get("name") or not customer.get("email")):
            raise ValueError("Customer name and email required")
        
        return True
    
    @staticmethod
    def validate_state_transition(
        current_status: OrderStatus,
        new_status: OrderStatus,
    ) -> bool:
        """
        Validate if state transition is allowed.
        
        Returns True if valid, raises ValueError if invalid.
        """
        valid_transitions = {
            OrderStatus.PENDING: [OrderStatus.AWAITING_PAYMENT, OrderStatus.CANCELLED, OrderStatus.PAYMENT_FAILED],
            OrderStatus.AWAITING_PAYMENT: [OrderStatus.PAID, OrderStatus.PAYMENT_FAILED, OrderStatus.CANCELLED],
            OrderStatus.PAYMENT_FAILED: [OrderStatus.AWAITING_PAYMENT, OrderStatus.CANCELLED],
            OrderStatus.PAID: [OrderStatus.PROCESSING, OrderStatus.CANCELLED],
            OrderStatus.PROCESSING: [OrderStatus.SHIPPING, OrderStatus.CANCELLED],
            OrderStatus.SHIPPING: [OrderStatus.DELIVERED],
            OrderStatus.DELIVERED: [OrderStatus.COMPLETED],
            OrderStatus.COMPLETED: [],  # Final state
            OrderStatus.CANCELLED: [],  # Final state
        }
        
        allowed = valid_transitions.get(current_status, [])
        if new_status not in allowed:
            raise ValueError(
                f"Invalid transition from {current_status} to {new_status}. "
                f"Allowed: {allowed}"
            )
        
        return True
    
    @staticmethod
    def validate_cancellation_allowed(order: Order) -> bool:
        """Check if order can be cancelled in current state."""
        if order.status in [OrderStatus.COMPLETED, OrderStatus.DELIVERED, OrderStatus.SHIPPING]:
            raise ValueError(
                f"Cannot cancel order in {order.status} state"
            )
        return True


class OrderStateTransitionService:
    """
    Service encapsulating order state machine logic.
    
    Coordinates transitions and side effects.
    """
    
    def __init__(self, order_repository: OrderRepository):
        self.order_repository = order_repository
    
    def transition_to_awaiting_payment(
        self,
        order: Order,
        payment_reference: str,
    ) -> None:
        """Transition order to awaiting_payment after stock reservation."""
        OrderValidator.validate_state_transition(
            order.status,
            OrderStatus.AWAITING_PAYMENT,
        )
        order.mark_awaiting_payment(payment_reference)
        self.order_repository.save(order)
    
    def handle_payment_success(self, order: Order) -> None:
        """Handle successful payment."""
        OrderValidator.validate_state_transition(
            order.status,
            OrderStatus.PAID,
        )
        order.mark_payment_success()
        self.order_repository.save(order)
    
    def handle_payment_failure(self, order: Order) -> None:
        """Handle failed payment."""
        order.mark_payment_failed()
        self.order_repository.save(order)
    
    def transition_to_processing(self, order: Order) -> None:
        """Transition to processing."""
        OrderValidator.validate_state_transition(
            order.status,
            OrderStatus.PROCESSING,
        )
        order.mark_processing()
        self.order_repository.save(order)
    
    def transition_to_shipping(
        self,
        order: Order,
        shipment_reference: Optional[str] = None,
    ) -> None:
        """Transition to shipping."""
        OrderValidator.validate_state_transition(
            order.status,
            OrderStatus.SHIPPING,
        )
        order.mark_shipping(shipment_reference)
        self.order_repository.save(order)
    
    def transition_to_delivered(self, order: Order) -> None:
        """Transition to delivered."""
        OrderValidator.validate_state_transition(
            order.status,
            OrderStatus.DELIVERED,
        )
        order.mark_delivered()
        self.order_repository.save(order)
    
    def transition_to_completed(self, order: Order) -> None:
        """Complete the order."""
        OrderValidator.validate_state_transition(
            order.status,
            OrderStatus.COMPLETED,
        )
        order.mark_completed()
        self.order_repository.save(order)
    
    def cancel_order(self, order: Order) -> None:
        """Cancel the order."""
        OrderValidator.validate_cancellation_allowed(order)
        order.mark_cancelled()
        self.order_repository.save(order)


class OrderCalculationService:
    """
    Service for order calculations (totals, quantities, etc).
    """
    
    @staticmethod
    def calculate_order_totals(
        items: List[OrderItem],
        shipping_fee: Money = None,
        discount: Money = None,
        tax_rate: Decimal = Decimal("0"),
    ) -> Dict[str, Money]:
        """
        Calculate all order totals.
        
        Returns dict with subtotal, shipping_fee, discount, tax, grand_total.
        """
        if not items:
            currency = Currency.VND
            zero = Money(Decimal("0"), currency)
            return {
                "subtotal": zero,
                "shipping_fee": zero or zero,
                "discount": zero or zero,
                "tax": zero,
                "grand_total": zero,
            }
        
        # Determine currency from first item
        currency = items[0].currency
        
        # Calculate subtotal
        subtotal_amount = sum(Decimal(str(item.line_total.amount)) for item in items)
        subtotal = Money(subtotal_amount, currency)
        
        # Use provided or default values
        shipping_fee = shipping_fee or Money(Decimal("0"), currency)
        discount = discount or Money(Decimal("0"), currency)
        
        # Calculate tax
        taxable_amount = subtotal.amount + shipping_fee.amount - discount.amount
        if tax_rate > 0:
            tax_amount = (taxable_amount * tax_rate).quantize(Decimal("0.01"))
        else:
            tax_amount = Decimal("0")
        tax = Money(tax_amount, currency)
        
        # Calculate grand total
        grand_total_amount = subtotal.amount + shipping_fee.amount - discount.amount + tax.amount
        grand_total = Money(grand_total_amount, currency)
        
        return {
            "subtotal": subtotal,
            "shipping_fee": shipping_fee,
            "discount": discount,
            "tax": tax,
            "grand_total": grand_total,
        }
    
    @staticmethod
    def calculate_total_quantity(items: List[OrderItem]) -> int:
        """Calculate total quantity of items."""
        return sum(item.quantity for item in items)
