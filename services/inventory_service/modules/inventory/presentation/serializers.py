"""
DRF serializers for Inventory service.

Handles request/response serialization and validation.
"""
from rest_framework import serializers
from datetime import datetime, timedelta


class ProductReferenceSerializer(serializers.Serializer):
    """Serializes product reference."""
    product_id = serializers.UUIDField()
    variant_id = serializers.UUIDField(required=False, allow_null=True)
    sku = serializers.CharField(required=False, allow_null=True, max_length=100)


class StockItemSerializer(serializers.Serializer):
    """Serializes stock item."""
    id = serializers.UUIDField()
    product_id = serializers.UUIDField()
    variant_id = serializers.UUIDField(required=False, allow_null=True)
    sku = serializers.CharField(required=False, allow_null=True, max_length=100)
    warehouse_code = serializers.CharField(max_length=50)
    on_hand_quantity = serializers.IntegerField()
    reserved_quantity = serializers.IntegerField()
    available_quantity = serializers.IntegerField()
    safety_stock = serializers.IntegerField()
    is_in_stock = serializers.BooleanField()
    is_low_stock = serializers.BooleanField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class CreateStockItemSerializer(serializers.Serializer):
    """Serializer for creating stock item."""
    product_id = serializers.UUIDField()
    variant_id = serializers.UUIDField(required=False, allow_null=True)
    sku = serializers.CharField(required=False, allow_null=True, max_length=100)
    warehouse_code = serializers.CharField(max_length=50, required=False, default="MAIN")
    on_hand_quantity = serializers.IntegerField(required=False, default=0, min_value=0)
    safety_stock = serializers.IntegerField(required=False, default=0, min_value=0)
    
    def validate_on_hand_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError("on_hand_quantity cannot be negative")
        return value


class UpdateStockItemSerializer(serializers.Serializer):
    """Serializer for updating stock item."""
    safety_stock = serializers.IntegerField(required=False, min_value=0)
    is_active = serializers.BooleanField(required=False)


class StockInSerializer(serializers.Serializer):
    """Serializer for stock in operation."""
    quantity = serializers.IntegerField(min_value=1)
    reference_id = serializers.CharField(required=False, allow_null=True, max_length=255)
    note = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class StockOutSerializer(serializers.Serializer):
    """Serializer for stock out operation."""
    quantity = serializers.IntegerField(min_value=1)
    reference_id = serializers.CharField(required=False, allow_null=True, max_length=255)
    note = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class AdjustStockSerializer(serializers.Serializer):
    """Serializer for stock adjustment."""
    quantity = serializers.IntegerField()  # Can be positive or negative
    reason = serializers.CharField(max_length=255)
    
    def validate_quantity(self, value):
        if value == 0:
            raise serializers.ValidationError("Adjustment quantity cannot be zero")
        return value


class StockMovementSerializer(serializers.Serializer):
    """Serializes stock movement."""
    id = serializers.UUIDField()
    stock_item_id = serializers.UUIDField()
    product_id = serializers.UUIDField()
    variant_id = serializers.UUIDField(required=False, allow_null=True)
    movement_type = serializers.CharField(max_length=30)
    quantity = serializers.IntegerField()
    reference_type = serializers.CharField(required=False, allow_null=True, max_length=30)
    reference_id = serializers.CharField(required=False, allow_null=True, max_length=255)
    note = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    created_at = serializers.DateTimeField()


# ===================== Reservation Serializers =====================

class StockReservationDetailSerializer(serializers.Serializer):
    """Detailed serializer for stock reservation."""
    id = serializers.UUIDField()
    product_id = serializers.UUIDField()
    variant_id = serializers.UUIDField(required=False, allow_null=True)
    quantity = serializers.IntegerField()
    status = serializers.CharField(max_length=20)
    order_id = serializers.UUIDField(required=False, allow_null=True)
    cart_id = serializers.UUIDField(required=False, allow_null=True)
    user_id = serializers.UUIDField(required=False, allow_null=True)
    expires_at = serializers.DateTimeField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class CreateReservationSerializer(serializers.Serializer):
    """Serializer for creating reservation."""
    product_id = serializers.UUIDField()
    variant_id = serializers.UUIDField(required=False, allow_null=True)
    quantity = serializers.IntegerField(required=False, default=1, min_value=1)
    order_id = serializers.UUIDField(required=False, allow_null=True)
    cart_id = serializers.UUIDField(required=False, allow_null=True)
    user_id = serializers.UUIDField(required=False, allow_null=True)
    expires_in_minutes = serializers.IntegerField(required=False, default=60, min_value=1)


class CheckAvailabilityItemSerializer(serializers.Serializer):
    """Item for availability check."""
    product_id = serializers.UUIDField()
    variant_id = serializers.UUIDField(required=False, allow_null=True)
    quantity = serializers.IntegerField(required=False, default=1, min_value=1)


class CheckAvailabilitySerializer(serializers.Serializer):
    """Serializer for checking availability."""
    items = CheckAvailabilityItemSerializer(many=True)


class AvailabilityResultSerializer(serializers.Serializer):
    """Result of availability check."""
    product_id = serializers.UUIDField()
    variant_id = serializers.UUIDField(required=False, allow_null=True)
    requested_quantity = serializers.IntegerField()
    available_quantity = serializers.IntegerField()
    can_reserve = serializers.BooleanField()
    is_in_stock = serializers.BooleanField()
    stock_item_id = serializers.UUIDField(required=False, allow_null=True)


class InventorySummarySerializer(serializers.Serializer):
    """Serializes inventory summary."""
    product_id = serializers.UUIDField()
    variant_id = serializers.UUIDField(required=False, allow_null=True)
    total_on_hand = serializers.IntegerField()
    total_reserved = serializers.IntegerField()
    total_available = serializers.IntegerField()
    warehouses = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )
