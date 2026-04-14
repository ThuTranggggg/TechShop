"""
Domain enums for Order context.

Defines all status and state enumerations.
"""

from enum import Enum


class OrderStatus(Enum):
    """
    Main order lifecycle status.
    
    pending -> awaiting_payment -> paid -> processing -> shipping -> delivered -> completed
                                      |
                                   payment_failed
    
    Any status can transition to cancelled under certain conditions.
    """
    
    PENDING = "pending"  # Order just created, orchestration in progress
    AWAITING_PAYMENT = "awaiting_payment"  # Stock reserved, waiting for payment
    PAID = "paid"  # Payment successful
    PROCESSING = "processing"  # Preparing for shipment
    SHIPPING = "shipping"  # In transit
    DELIVERED = "delivered"  # Delivered to customer
    COMPLETED = "completed"  # Fully completed
    CANCELLED = "cancelled"  # Order cancelled
    PAYMENT_FAILED = "payment_failed"  # Payment failed
    
    def __str__(self):
        return self.value
    
    def __repr__(self):
        return f"OrderStatus.{self.name}"


class PaymentStatus(Enum):
    """
    Payment status within an order.
    
    independent from order status to track payment lifecycle precisely.
    """
    
    UNPAID = "unpaid"  # No payment attempted
    PENDING = "pending"  # Payment initiated, awaiting result
    AUTHORIZED = "authorized"  # Payment authorized but not captured
    PAID = "paid"  # Payment successfully captured
    FAILED = "failed"  # Payment failed
    REFUNDED = "refunded"  # Full refund
    PARTIALLY_REFUNDED = "partially_refunded"  # Partial refund
    
    def __str__(self):
        return self.value
    
    def __repr__(self):
        return f"PaymentStatus.{self.name}"


class FulfillmentStatus(Enum):
    """
    Fulfillment status tracking shipment/delivery.
    
    independent from order status to track logistics precisely.
    """
    
    UNFULFILLED = "unfulfilled"  # No shipment yet
    PREPARING = "preparing"  # Being prepared for shipment
    SHIPPED = "shipped"  # In transit
    DELIVERED = "delivered"  # Delivered
    RETURNED = "returned"  # Returned by customer
    CANCELLED = "cancelled"  # Fulfillment cancelled
    
    def __str__(self):
        return self.value
    
    def __repr__(self):
        return f"FulfillmentStatus.{self.name}"


class OrderEventType(Enum):
    """
    Event types that can occur on an order.
    Used for status history and audit trail.
    """
    
    CREATED = "created"
    PAYMENT_INITIATED = "payment_initiated"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    STOCK_RESERVED = "stock_reserved"
    STOCK_RESERVE_FAILED = "stock_reserve_failed"
    STOCK_CONFIRMED = "stock_confirmed"
    STOCK_RELEASED = "stock_released"
    SHIPMENT_CREATED = "shipment_created"
    SHIPMENT_UPDATED = "shipment_updated"
    MARKED_PROCESSING = "marked_processing"
    MARKED_SHIPPING = "marked_shipping"
    MARKED_DELIVERED = "marked_delivered"
    MARKED_COMPLETED = "marked_completed"
    CANCELLED = "cancelled"
    REFUND_INITIATED = "refund_initiated"
    REFUND_SUCCESS = "refund_success"
    
    def __str__(self):
        return self.value


class Currency(Enum):
    """
    Supported currencies.
    """
    
    USD = "USD"
    VND = "VND"
    EUR = "EUR"
    
    def __str__(self):
        return self.value
