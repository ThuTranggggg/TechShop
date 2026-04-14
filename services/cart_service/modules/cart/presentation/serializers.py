"""
DRF Serializers for Cart APIs.

Handles request/response serialization and validation.
"""
from rest_framework import serializers
from decimal import Decimal
from typing import Optional


class CartItemSerializer(serializers.Serializer):
    """Serializer for cart item response."""
    id = serializers.CharField(read_only=True)
    product_id = serializers.CharField()
    variant_id = serializers.CharField(required=False, allow_null=True)
    product_name = serializers.CharField()
    product_slug = serializers.CharField()
    variant_name = serializers.CharField(required=False, allow_null=True)
    brand_name = serializers.CharField(required=False, allow_null=True)
    category_name = serializers.CharField(required=False, allow_null=True)
    sku = serializers.CharField(required=False, allow_null=True)
    thumbnail_url = serializers.URLField(required=False, allow_null=True)
    quantity = serializers.IntegerField(min_value=1)
    # FIXED: Changed from CharField to DecimalField for proper numeric handling
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField()
    # FIXED: Changed from CharField to DecimalField for proper numeric handling
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2)
    status = serializers.CharField()
    availability_checked_at = serializers.DateTimeField(required=False, allow_null=True)


class CartSerializer(serializers.Serializer):
    """Serializer for cart response."""
    id = serializers.CharField(read_only=True)
    user_id = serializers.CharField(read_only=True)
    status = serializers.CharField()
    currency = serializers.CharField()
    # FIXED: Changed from CharField to DecimalField for proper numeric handling
    subtotal_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_quantity = serializers.IntegerField()
    item_count = serializers.IntegerField()
    items = CartItemSerializer(many=True, read_only=True)
    last_activity_at = serializers.DateTimeField(required=False, allow_null=True)
    created_at = serializers.DateTimeField(required=False, allow_null=True)
    updated_at = serializers.DateTimeField(required=False, allow_null=True)


class AddItemToCartSerializer(serializers.Serializer):
    """Serializer for adding item to cart."""
    product_id = serializers.CharField(required=True, min_length=1)
    variant_id = serializers.CharField(required=False, allow_null=True)
    quantity = serializers.IntegerField(required=True, min_value=1)
    
    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return value


class UpdateCartItemSerializer(serializers.Serializer):
    """Serializer for updating cart item quantity."""
    new_quantity = serializers.IntegerField(required=True, min_value=1)
    
    def validate_new_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return value


class IncreaseDecreaseQuantitySerializer(serializers.Serializer):
    """Serializer for increasing/decreasing quantity."""
    amount = serializers.IntegerField(required=False, default=1, min_value=1)
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value


class CartValidationIssueSerializer(serializers.Serializer):
    """Serializer for validation issue."""
    item_id = serializers.CharField(required=False, allow_null=True)
    product_id = serializers.CharField()
    status = serializers.CharField()
    message = serializers.CharField()


class CartValidationResultSerializer(serializers.Serializer):
    """Serializer for cart validation result."""
    is_valid = serializers.BooleanField()
    issues = CartValidationIssueSerializer(many=True)


class CheckoutPreviewSerializer(serializers.Serializer):
    """Serializer for checkout preview response."""
    is_valid = serializers.BooleanField()
    cart = CartSerializer()
    issues = CartValidationIssueSerializer(many=True)
    checkout_payload = serializers.JSONField(required=False, allow_null=True)


class CartSummarySerializer(serializers.Serializer):
    """Serializer for cart summary response."""
    item_count = serializers.IntegerField()
    total_quantity = serializers.IntegerField()
    # FIXED: Changed from CharField to DecimalField for proper numeric handling
    subtotal_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField()
