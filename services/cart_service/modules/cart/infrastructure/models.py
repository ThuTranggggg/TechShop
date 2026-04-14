"""
Django ORM models for Cart infrastructure layer.

These models persist domain entities.
"""
import uuid
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

from ..domain.enums import CartStatus, CartItemStatus


class CartModel(models.Model):
    """
    Django model for Cart aggregate root.
    
    Represents a user's shopping cart.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # User reference
    user_id = models.UUIDField(
        db_index=True,
        help_text="UUID of user who owns this cart"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[(status.value, status.value) for status in CartStatus],
        default=CartStatus.ACTIVE.value,
        db_index=True,
        help_text="Current cart status"
    )
    
    # Currency and amounts
    currency = models.CharField(
        max_length=3,
        default="USD",
        help_text="Currency code (ISO 4217)"
    )
    subtotal_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Subtotal before tax/shipping"
    )
    
    # Counts
    total_quantity = models.BigIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Total quantity of all items"
    )
    item_count = models.BigIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Number of unique items"
    )
    
    # Timestamps
    last_activity_at = models.DateTimeField(
        auto_now=True,
        help_text="Last time cart was modified"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When cart was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When cart was last updated"
    )
    
    class Meta:
        app_label = "cart"
        indexes = [
            models.Index(fields=["user_id", "status"]),
            models.Index(fields=["status", "updated_at"]),
        ]
        # Constraint: only one active cart per user
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "status"],
                condition=models.Q(status=CartStatus.ACTIVE.value),
                name="one_active_cart_per_user",
            )
        ]
    
    def __str__(self):
        return f"Cart({self.user_id}, {self.status})"


class CartItemModel(models.Model):
    """
    Django model for CartItem entity.
    
    Represents a product in a user's cart with quantity and snapshot.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Cart reference (FK)
    cart = models.ForeignKey(
        CartModel,
        on_delete=models.CASCADE,
        db_index=True,
        related_name="items",
        help_text="Parent cart"
    )
    
    # Product reference (from product_service)
    product_id = models.UUIDField(
        db_index=True,
        help_text="UUID of product from product_service"
    )
    variant_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="UUID of product variant (nullable if product has no variants)"
    )
    
    # Quantity
    quantity = models.BigIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Quantity of this item in cart"
    )
    
    # Price snapshot (for display stability)
    unit_price_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Unit price at time of adding to cart"
    )
    currency = models.CharField(
        max_length=3,
        default="USD",
        help_text="Currency code"
    )
    
    # Product snapshot (minimal fields for stable display)
    product_name_snapshot = models.CharField(
        max_length=255,
        help_text="Product name at time of adding"
    )
    product_slug_snapshot = models.CharField(
        max_length=255,
        help_text="Product slug for linking"
    )
    variant_name_snapshot = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Variant name if applicable"
    )
    brand_name_snapshot = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Brand name at time of adding"
    )
    category_name_snapshot = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Category name at time of adding"
    )
    sku = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="SKU from product_service"
    )
    thumbnail_url_snapshot = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Thumbnail URL at time of adding"
    )
    attributes_snapshot = models.JSONField(
        default=dict,
        help_text="Product attributes snapshot (JSON)"
    )
    
    # Availability tracking
    status = models.CharField(
        max_length=30,
        choices=[(s.value, s.value) for s in CartItemStatus],
        default=CartItemStatus.AVAILABLE.value,
        help_text="Current item status (availability)"
    )
    availability_checked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When availability was last checked"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When item was added to cart"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When item was last updated"
    )
    
    class Meta:
        app_label = "cart"
        indexes = [
            models.Index(fields=["cart", "product_id", "variant_id"]),
            models.Index(fields=["cart", "status"]),
        ]
        # Unique constraint: prevent duplicate products in cart
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "product_id", "variant_id"],
                name="unique_product_in_cart",
            )
        ]
    
    def __str__(self):
        return f"CartItem({self.product_name_snapshot}, qty={self.quantity})"
