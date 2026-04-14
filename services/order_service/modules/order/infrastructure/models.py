"""
Infrastructure models for Order context.

ORM models for persistence using Django ORM.
"""

import uuid
from decimal import Decimal
from django.db import models
from django.contrib.postgres.fields import ArrayField

from ..domain.enums import (
    OrderStatus, PaymentStatus, FulfillmentStatus, OrderEventType, Currency
)


class OrderModel(models.Model):
    """
    Persistence model for Order aggregate root.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(
        max_length=32, unique=True, db_index=True,
        help_text="Human-readable order number (ORD-YYYYMMDD-XXXXXX)"
    )
    user_id = models.UUIDField(db_index=True, help_text="Customer user ID (from user_service)")
    cart_id = models.UUIDField(
        null=True, blank=True, db_index=True,
        help_text="Source cart ID (reference only)"
    )
    
    # Status fields
    status = models.CharField(
        max_length=32,
        choices=[(s.value, s.value) for s in OrderStatus],
        default=OrderStatus.PENDING.value,
        db_index=True,
    )
    payment_status = models.CharField(
        max_length=32,
        choices=[(s.value, s.value) for s in PaymentStatus],
        default=PaymentStatus.UNPAID.value,
        db_index=True,
    )
    fulfillment_status = models.CharField(
        max_length=32,
        choices=[(s.value, s.value) for s in FulfillmentStatus],
        default=FulfillmentStatus.UNFULFILLED.value,
        db_index=True,
    )
    currency = models.CharField(
        max_length=3,
        choices=[(c.value, c.value) for c in Currency],
        default=Currency.VND.value,
    )
    
    # Pricing fields (in smallest unit: VND, cents for USD/EUR, etc)
    subtotal_amount = models.DecimalField(max_digits=19, decimal_places=2, default=Decimal("0"))
    shipping_fee_amount = models.DecimalField(max_digits=19, decimal_places=2, default=Decimal("0"))
    discount_amount = models.DecimalField(max_digits=19, decimal_places=2, default=Decimal("0"))
    tax_amount = models.DecimalField(max_digits=19, decimal_places=2, default=Decimal("0"))
    grand_total_amount = models.DecimalField(max_digits=19, decimal_places=2, default=Decimal("0"))
    
    # Quantity fields
    total_quantity = models.IntegerField(default=0, help_text="Total quantity of all items")
    item_count = models.IntegerField(default=0, help_text="Number of unique order items")
    
    # Customer snapshot
    customer_name_snapshot = models.CharField(max_length=255)
    customer_email_snapshot = models.EmailField()
    customer_phone_snapshot = models.CharField(max_length=20, blank=True, default="")
    
    # Shipping address snapshot
    receiver_name = models.CharField(max_length=255)
    receiver_phone = models.CharField(max_length=20)
    shipping_line1 = models.CharField(max_length=255)
    shipping_line2 = models.CharField(max_length=255, blank=True, default="")
    shipping_ward = models.CharField(max_length=100, blank=True, default="")
    shipping_district = models.CharField(max_length=100)
    shipping_city = models.CharField(max_length=100)
    shipping_country = models.CharField(max_length=100, default="Vietnam")
    shipping_postal_code = models.CharField(max_length=20, blank=True, default="")
    address_requires_verification = models.BooleanField(
        default=False,
        help_text="Flag if address requires manual verification (for admin review)"
    )
    address_verification_note = models.TextField(
        blank=True, default="",
        help_text="Note explaining why address requires verification"
    )
    
    # References to external services
    payment_id = models.UUIDField(null=True, blank=True, help_text="Payment service order ID")
    payment_reference = models.CharField(max_length=255, blank=True, default="")
    payment_success_processed_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Timestamp when payment_success callback was processed (for idempotency)"
    )
    shipment_id = models.UUIDField(null=True, blank=True, help_text="Shipping service shipment ID")
    shipment_reference = models.CharField(max_length=255, blank=True, default="")
    
    # Stock reservation references (JSON array)
    stock_reservation_refs = models.JSONField(
        default=list,
        help_text="Array of stock reservation references from inventory_service"
    )
    
    # Additional info
    notes = models.TextField(blank=True, default="")
    
    # Milestones
    placed_at = models.DateTimeField(null=True, blank=True, help_text="When order was successfully placed")
    paid_at = models.DateTimeField(null=True, blank=True, help_text="When payment was confirmed")
    cancelled_at = models.DateTimeField(null=True, blank=True, help_text="When order was cancelled")
    completed_at = models.DateTimeField(null=True, blank=True, help_text="When order was completed")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "order_ordermodel"
        indexes = [
            models.Index(fields=["order_number"]),
            models.Index(fields=["user_id"]),
            models.Index(fields=["status"]),
            models.Index(fields=["payment_status"]),
            models.Index(fields=["fulfillment_status"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["placed_at"]),
            models.Index(fields=["user_id", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]
        verbose_name = "Order"
        verbose_name_plural = "Orders"
    
    def __str__(self):
        return f"Order {self.order_number} ({self.status})"


class OrderItemModel(models.Model):
    """
    Persistence model for OrderItem (line items in an order).
    
    Snapshot of product information at time of purchase.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        OrderModel, on_delete=models.CASCADE, related_name="items"
    )
    
    # Product reference
    product_id = models.UUIDField(db_index=True, help_text="Product ID from product_service")
    variant_id = models.UUIDField(
        null=True, blank=True, help_text="Product variant ID if applicable"
    )
    sku = models.CharField(max_length=100, blank=True, default="")
    
    # Line pricing
    quantity = models.IntegerField(help_text="Quantity ordered")
    unit_price = models.DecimalField(
        max_digits=19, decimal_places=2, help_text="Price per unit at time of purchase"
    )
    line_total = models.DecimalField(
        max_digits=19, decimal_places=2, help_text="Quantity * unit_price"
    )
    currency = models.CharField(
        max_length=3,
        choices=[(c.value, c.value) for c in Currency],
        default=Currency.VND.value,
    )
    
    # Product snapshot
    product_name_snapshot = models.CharField(max_length=255, help_text="Product name at purchase time")
    product_slug_snapshot = models.CharField(max_length=255, help_text="Product slug at purchase time")
    variant_name_snapshot = models.CharField(
        max_length=255, blank=True, default="", help_text="Variant name if applicable"
    )
    brand_name_snapshot = models.CharField(max_length=255, blank=True, default="")
    category_name_snapshot = models.CharField(max_length=255, blank=True, default="")
    thumbnail_url_snapshot = models.URLField(blank=True, default="")
    
    # Attributes snapshot (JSON)
    attributes_snapshot = models.JSONField(default=dict)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "order_orderitemmodel"
        indexes = [
            models.Index(fields=["order_id"]),
            models.Index(fields=["product_id"]),
            models.Index(fields=["variant_id"]),
            models.Index(fields=["sku"]),
        ]
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"
    
    def __str__(self):
        return f"OrderItem {self.product_name_snapshot} (qty={self.quantity})"


class OrderStatusHistoryModel(models.Model):
    """
    Persistence model for order status change history.
    
    Audit trail of all status transitions.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        OrderModel, on_delete=models.CASCADE, related_name="status_history"
    )
    
    # Status transition
    from_status = models.CharField(
        max_length=32, null=True, blank=True,
        help_text="Previous status (null for initial)"
    )
    to_status = models.CharField(
        max_length=32,
        help_text="New status"
    )
    
    # Metadata
    note = models.TextField(blank=True, default="")
    changed_by = models.UUIDField(
        null=True, blank=True,
        help_text="User who made the change (null if system)"
    )
    metadata = models.JSONField(default=dict, help_text="Additional metadata about the transition")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "order_orderstatushistorymodel"
        indexes = [
            models.Index(fields=["order_id"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["to_status"]),
        ]
        ordering = ["created_at"]
        verbose_name = "Order Status History"
        verbose_name_plural = "Order Status Histories"
    
    def __str__(self):
        return f"{self.order.order_number}: {self.from_status} -> {self.to_status}"
