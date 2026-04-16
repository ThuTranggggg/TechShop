"""
Presentation serializers for Order API.

DRF serializers for request/response serialization.
"""

from rest_framework import serializers
from typing import Dict, Any
from uuid import UUID
from decimal import Decimal

from ..domain import OrderStatus, PaymentStatus, FulfillmentStatus
from ..application.dtos import (
    OrderDetailDTO, OrderListItemDTO, OrderItemDTO, StatusHistoryItemDTO,
    OrderTimelineDTO
)


class OrderItemSerializer(serializers.Serializer):
    """Serializer for order item."""
    
    id = serializers.UUIDField(read_only=True)
    product_id = serializers.UUIDField()
    product_name = serializers.CharField(read_only=True)
    product_slug = serializers.CharField(read_only=True)
    variant_id = serializers.UUIDField(required=False, allow_null=True)
    variant_name = serializers.CharField(required=False, allow_null=True)
    sku = serializers.CharField(required=False, allow_null=True)
    quantity = serializers.IntegerField()
    unit_price = serializers.DecimalField(max_digits=19, decimal_places=2)
    line_total = serializers.DecimalField(max_digits=19, decimal_places=2, read_only=True)
    currency = serializers.CharField(read_only=True)
    brand_name = serializers.CharField(required=False, allow_null=True)
    category_name = serializers.CharField(required=False, allow_null=True)
    thumbnail_url = serializers.URLField(required=False, allow_null=True)
    attributes = serializers.JSONField(default=dict)


class OrderTotalsSerializer(serializers.Serializer):
    """Serializer for order totals."""
    
    subtotal = serializers.DecimalField(max_digits=19, decimal_places=2)
    shipping_fee = serializers.DecimalField(max_digits=19, decimal_places=2)
    discount = serializers.DecimalField(max_digits=19, decimal_places=2)
    tax = serializers.DecimalField(max_digits=19, decimal_places=2)
    grand_total = serializers.DecimalField(max_digits=19, decimal_places=2)
    currency = serializers.CharField()


class AddressSnapshotSerializer(serializers.Serializer):
    """Serializer for shipping address."""
    
    receiver_name = serializers.CharField()
    receiver_phone = serializers.CharField()
    line1 = serializers.CharField()
    line2 = serializers.CharField(required=False, allow_null=True)
    ward = serializers.CharField(required=False, allow_null=True)
    district = serializers.CharField()
    city = serializers.CharField()
    country = serializers.CharField()
    postal_code = serializers.CharField(required=False, allow_null=True)


class OrderDetailSerializer(serializers.Serializer):
    """Serializer for full order details."""
    
    id = serializers.UUIDField()
    order_number = serializers.CharField()
    status = serializers.CharField()
    payment_status = serializers.CharField()
    fulfillment_status = serializers.CharField()
    items = OrderItemSerializer(many=True)
    totals = OrderTotalsSerializer()
    customer_name = serializers.CharField()
    customer_email = serializers.EmailField()
    customer_phone = serializers.CharField(required=False, allow_null=True)
    shipping_address = AddressSnapshotSerializer()
    payment_id = serializers.UUIDField(required=False, allow_null=True)
    payment_reference = serializers.CharField(required=False, allow_null=True)
    shipment_id = serializers.UUIDField(required=False, allow_null=True)
    shipment_reference = serializers.CharField(required=False, allow_null=True)
    total_quantity = serializers.IntegerField()
    item_count = serializers.IntegerField()
    notes = serializers.CharField(required=False, allow_blank=True)
    placed_at = serializers.DateTimeField(required=False, allow_null=True)
    paid_at = serializers.DateTimeField(required=False, allow_null=True)
    cancelled_at = serializers.DateTimeField(required=False, allow_null=True)
    completed_at = serializers.DateTimeField(required=False, allow_null=True)
    created_at = serializers.DateTimeField(required=False, allow_null=True)
    updated_at = serializers.DateTimeField(required=False, allow_null=True)


class OrderListItemSerializer(serializers.Serializer):
    """Serializer for order list item."""
    
    id = serializers.UUIDField()
    order_number = serializers.CharField()
    status = serializers.CharField()
    payment_status = serializers.CharField()
    grand_total = serializers.DecimalField(max_digits=19, decimal_places=2)
    currency = serializers.CharField()
    total_quantity = serializers.IntegerField()
    item_count = serializers.IntegerField()
    placed_at = serializers.DateTimeField(required=False, allow_null=True)
    created_at = serializers.DateTimeField(required=False, allow_null=True)


class CreateOrderFromCartSerializer(serializers.Serializer):
    """Serializer for create order from cart request."""
    
    cart_id = serializers.UUIDField()
    shipping_address = serializers.JSONField()
    customer = serializers.JSONField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_customer(self, value):
        if value and (not value.get("name") or not value.get("email")):
            raise serializers.ValidationError("Customer name and email required")
        return value
    
    def validate_shipping_address(self, value):
        """Validate shipping address fields."""
        required_fields = ["receiver_name", "receiver_phone", "line1", "district", "city"]
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"Missing required field: {field}")
        return value


class StatusHistoryItemSerializer(serializers.Serializer):
    """Serializer for status history item."""
    
    from_status = serializers.CharField(required=False, allow_null=True)
    to_status = serializers.CharField()
    note = serializers.CharField(required=False, allow_blank=True)
    changed_by = serializers.UUIDField(required=False, allow_null=True)
    created_at = serializers.DateTimeField(required=False, allow_null=True)


class OrderTimelineSerializer(serializers.Serializer):
    """Serializer for order timeline."""
    
    order_id = serializers.UUIDField()
    order_number = serializers.CharField()
    status_history = StatusHistoryItemSerializer(many=True)
    placed_at = serializers.DateTimeField(required=False, allow_null=True)
    paid_at = serializers.DateTimeField(required=False, allow_null=True)
    shipped_at = serializers.DateTimeField(required=False, allow_null=True)
    delivered_at = serializers.DateTimeField(required=False, allow_null=True)
    completed_at = serializers.DateTimeField(required=False, allow_null=True)
    cancelled_at = serializers.DateTimeField(required=False, allow_null=True)


class CancelOrderSerializer(serializers.Serializer):
    """Serializer for cancel order request."""
    
    reason = serializers.CharField(required=False, allow_blank=True, default="User cancelled")
