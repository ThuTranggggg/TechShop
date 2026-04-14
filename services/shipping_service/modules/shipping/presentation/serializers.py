"""
Shipment REST API Serializers

DRF serializers for validation and representation.
"""

from rest_framework import serializers
from decimal import Decimal
from uuid import UUID


class ShipmentItemSerializer(serializers.Serializer):
    """Serializer for shipment  items"""
    order_item_id = serializers.UUIDField(required=False, allow_null=True)
    product_id = serializers.UUIDField(required=True)
    variant_id = serializers.UUIDField(required=False, allow_null=True)
    sku = serializers.CharField(required=False, allow_blank=True, max_length=50)
    quantity = serializers.IntegerField(required=True, min_value=1)
    product_name_snapshot = serializers.CharField(required=True, max_length=255)
    variant_name_snapshot = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=255)


class CreateShipmentSerializer(serializers.Serializer):
    """Serializer for creating shipment"""
    order_id = serializers.UUIDField(required=True)
    order_number = serializers.CharField(required=True, max_length=50)
    user_id = serializers.UUIDField(required=False, allow_null=True)
    receiver_name = serializers.CharField(required=True, max_length=100)
    receiver_phone = serializers.CharField(required=True, max_length=20)
    address_line1 = serializers.CharField(required=True, max_length=255)
    address_line2 = serializers.CharField(required=False, allow_blank=True, max_length=255)
    ward = serializers.CharField(required=False, allow_blank=True, max_length=100)
    district = serializers.CharField(required=True, max_length=100)
    city = serializers.CharField(required=True, max_length=100)
    country = serializers.CharField(required=False, default="VN", max_length=100)
    postal_code = serializers.CharField(required=False, allow_blank=True, max_length=20)
    items = ShipmentItemSerializer(many=True, required=True)
    service_level = serializers.CharField(required=False, default="standard", max_length=20)
    provider = serializers.CharField(required=False, default="mock", max_length=20)
    shipping_fee_amount = serializers.DecimalField(required=False, decimal_places=2, max_digits=12, allow_null=True)
    currency = serializers.CharField(required=False, default="VND", max_length=3)
    idempotency_key = serializers.CharField(required=False, allow_blank=True)


class ShipmentItemResponseSerializer(serializers.Serializer):
    """Response serializer for shipment items"""
    order_item_id = serializers.CharField(allow_null=True)
    product_id = serializers.CharField()
    variant_id = serializers.CharField(allow_null=True)
    sku = serializers.CharField(allow_null=True)
    quantity = serializers.IntegerField()
    product_name_snapshot = serializers.CharField()
    variant_name_snapshot = serializers.CharField(allow_null=True)


class ShipmentTrackingEventSerializer(serializers.Serializer):
    """Response serializer for tracking events"""
    id = serializers.CharField()
    event_type = serializers.CharField()
    status_after = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    location = serializers.CharField(allow_null=True)
    event_time = serializers.CharField(allow_null=True)
    created_at = serializers.CharField(allow_null=True)


class ShipmentDetailResponseSerializer(serializers.Serializer):
    """Response serializer for shipment detail"""
    id = serializers.CharField()
    shipment_reference = serializers.CharField()
    tracking_number = serializers.CharField()
    order_id = serializers.CharField()
    order_number = serializers.CharField()
    user_id = serializers.CharField(allow_null=True)
    provider = serializers.CharField()
    service_level = serializers.CharField()
    status = serializers.CharField()
    tracking_url = serializers.CharField(allow_null=True)
    label_url = serializers.CharField(allow_null=True)
    package_count = serializers.IntegerField()
    package_weight = serializers.CharField(allow_null=True)
    shipping_fee_amount = serializers.CharField(allow_null=True)
    currency = serializers.CharField()
    failure_reason = serializers.CharField(allow_null=True)
    carrier_shipment_id = serializers.CharField(allow_null=True)
    expected_delivery_at = serializers.CharField(allow_null=True)
    shipped_at = serializers.CharField(allow_null=True)
    delivered_at = serializers.CharField(allow_null=True)
    cancelled_at = serializers.CharField(allow_null=True)
    created_at = serializers.CharField(allow_null=True)
    updated_at = serializers.CharField(allow_null=True)
    receiver_name = serializers.CharField()
    receiver_phone = serializers.CharField()
    address_line1 = serializers.CharField()
    district = serializers.CharField()
    city = serializers.CharField()
    country = serializers.CharField()
    items = ShipmentItemResponseSerializer(many=True)
    latest_event = ShipmentTrackingEventSerializer(allow_null=True)
    events_count = serializers.IntegerField()


class ShipmentStatusResponseSerializer(serializers.Serializer):
    """Response serializer for quick status"""
    shipment_reference = serializers.CharField()
    tracking_number = serializers.CharField()
    status = serializers.CharField()
    provider = serializers.CharField()
    order_id = serializers.CharField()
    created_at = serializers.CharField(allow_null=True)
    updated_at = serializers.CharField(allow_null=True)
    expected_delivery_at = serializers.CharField(allow_null=True)
    delivered_at = serializers.CharField(allow_null=True)
    current_location = serializers.CharField(allow_null=True)


class ShipmentTrackingResponseSerializer(serializers.Serializer):
    """Response serializer for public tracking"""
    shipment_reference = serializers.CharField()
    tracking_number = serializers.CharField()
    status = serializers.CharField()
    provider = serializers.CharField()
    tracking_url = serializers.CharField(allow_null=True)
    expected_delivery_at = serializers.CharField(allow_null=True)
    delivered_at = serializers.CharField(allow_null=True)
    current_location = serializers.CharField(allow_null=True)
    events = ShipmentTrackingEventSerializer(many=True)
    receiver_city = serializers.CharField(allow_null=True)


class AdvanceMockStatusSerializer(serializers.Serializer):
    """Serializer for advancing mock shipment status"""
    target_status = serializers.CharField(required=True)
