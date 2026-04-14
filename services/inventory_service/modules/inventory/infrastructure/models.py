"""
Django ORM models for Inventory infrastructure layer.

These models persist domain entities.
"""
import uuid
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone

from ..domain.enums import ReservationStatus, StockMovementType, WarehouseType


class StockItemModel(models.Model):
    """
    Django model for StockItem aggregate root.
    
    Represents inventory of a product/variant at a warehouse.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
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
    sku = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="SKU from product_service"
    )
    
    # Warehouse/Location
    warehouse_code = models.CharField(
        max_length=50,
        db_index=True,
        default="MAIN",
        help_text="Warehouse or location code"
    )
    
    # Stock quantities
    on_hand_quantity = models.BigIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Actual stock on hand"
    )
    reserved_quantity = models.BigIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Total quantity in active reservations"
    )
    
    # Safety stock threshold
    safety_stock = models.BigIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Minimum stock level for alerts"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this stock item is active"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "stock_items"
        verbose_name = "Stock Item"
        verbose_name_plural = "Stock Items"
        
        # Unique constraint - one inventory per product/variant per warehouse
        constraints = [
            models.UniqueConstraint(
                fields=["product_id", "variant_id", "warehouse_code"],
                name="unique_stock_per_warehouse",
                condition=models.Q(is_active=True),
            ),
            # Check constraints for quantities
            models.CheckConstraint(
                check=models.Q(on_hand_quantity__gte=0),
                name="on_hand_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(reserved_quantity__gte=0),
                name="reserved_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(reserved_quantity__lte=models.F("on_hand_quantity")),
                name="reserved_not_exceeds_onhand",
            ),
        ]
        
        indexes = [
            models.Index(fields=["product_id", "warehouse_code"]),
            models.Index(fields=["variant_id", "warehouse_code"]),
            models.Index(fields=["is_active", "on_hand_quantity"]),
            models.Index(fields=["updated_at"]),
        ]
    
    def __str__(self):
        return f"Stock#{self.product_id[:8]} (warehouse={self.warehouse_code})"
    
    @property
    def available_quantity(self) -> int:
        """Calculate available quantity (on-hand - reserved)."""
        return self.on_hand_quantity - self.reserved_quantity
    
    def is_in_stock(self) -> bool:
        """Check if item is in stock."""
        return self.available_quantity > 0
    
    def is_low_stock(self) -> bool:
        """Check if item is low stock."""
        return self.on_hand_quantity <= self.safety_stock


class StockReservationModel(models.Model):
    """
    Django model for StockReservation entity.
    
    Temporary reserve of stock for cart/order.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Unique reservation code for idempotency
    reservation_code = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Unique code for this reservation (for idempotency)"
    )
    
    # Stock item reference
    stock_item = models.ForeignKey(
        StockItemModel,
        on_delete=models.PROTECT,
        related_name="reservations",
        help_text="Reference to stock item being reserved"
    )
    
    # Product reference (for quick access without FK join)
    product_id = models.UUIDField(db_index=True)
    variant_id = models.UUIDField(null=True, blank=True, db_index=True)
    
    # Order/Cart reference
    order_id = models.UUIDField(null=True, blank=True, db_index=True)
    cart_id = models.UUIDField(null=True, blank=True, db_index=True)
    user_id = models.UUIDField(null=True, blank=True, db_index=True)
    
    # Reservation details
    quantity = models.BigIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Quantity reserved"
    )
    
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.value) for s in ReservationStatus],
        default=ReservationStatus.ACTIVE.value,
        db_index=True,
        help_text="Current reservation status"
    )
    
    # Expiration
    expires_at = models.DateTimeField(
        db_index=True,
        help_text="When this reservation expires"
    )
    
    # Metadata for extensibility
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata as JSON"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "stock_reservations"
        verbose_name = "Stock Reservation"
        verbose_name_plural = "Stock Reservations"
        
        indexes = [
            models.Index(fields=["status", "expires_at"]),
            models.Index(fields=["order_id", "status"]),
            models.Index(fields=["cart_id", "status"]),
            models.Index(fields=["product_id", "status"]),
            models.Index(fields=["user_id", "status"]),
            models.Index(fields=["created_at"]),
        ]
    
    def __str__(self):
        return f"Reservation#{self.reservation_code} (product={self.product_id[:8]}, qty={self.quantity})"
    
    def is_expired(self) -> bool:
        """Check if reservation has expired."""
        return timezone.now() > self.expires_at
    
    def is_active(self) -> bool:
        """Check if reservation is active."""
        return (
            self.status == ReservationStatus.ACTIVE.value
            and not self.is_expired()
        )


class StockMovementModel(models.Model):
    """
    Django model for StockMovement entity.
    
    Audit trail of all inventory changes.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Stock item reference
    stock_item = models.ForeignKey(
        StockItemModel,
        on_delete=models.PROTECT,
        related_name="movements",
        help_text="Reference to stock item"
    )
    
    # Product reference (for quick access)
    product_id = models.UUIDField(db_index=True)
    variant_id = models.UUIDField(null=True, blank=True, db_index=True)
    
    # Movement type and quantity
    movement_type = models.CharField(
        max_length=30,
        choices=[(t.value, t.value) for t in StockMovementType],
        db_index=True,
        help_text="Type of inventory movement"
    )
    
    quantity = models.BigIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Quantity involved in this movement"
    )
    
    # Reference for traceability
    reference_type = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        help_text="Type of reference (order, purchase_order, etc.)"
    )
    
    reference_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        help_text="ID of referenced entity (order_id, purchase_order_id, etc.)"
    )
    
    # Notes and metadata
    note = models.TextField(
        null=True,
        blank=True,
        help_text="Reason or note for this movement"
    )
    
    created_by = models.UUIDField(
        null=True,
        blank=True,
        help_text="User who created this movement"
    )
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata as JSON"
    )
    
    # Timestamp (immutable)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = "stock_movements"
        verbose_name = "Stock Movement"
        verbose_name_plural = "Stock Movements"
        
        # Movements are immutable - no update needed
        get_latest_by = "created_at"
        
        indexes = [
            models.Index(fields=["stock_item", "created_at"]),
            models.Index(fields=["product_id", "created_at"]),
            models.Index(fields=["movement_type", "created_at"]),
            models.Index(fields=["reference_type", "reference_id"]),
        ]
    
    def __str__(self):
        return f"Movement#{self.id} ({self.movement_type}, qty={self.quantity})"


class WarehouseModel(models.Model):
    """
    Optional Django model for Warehouse master data.
    
    Can be extended for multi-warehouse support.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Warehouse code"
    )
    
    name = models.CharField(
        max_length=200,
        help_text="Warehouse name"
    )
    
    warehouse_type = models.CharField(
        max_length=20,
        choices=[(w.value, w.value) for w in WarehouseType],
        default=WarehouseType.MAIN.value,
        help_text="Type of warehouse"
    )
    
    location = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Physical location/address"
    )
    
    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "warehouses"
        verbose_name = "Warehouse"
        verbose_name_plural = "Warehouses"
    
    def __str__(self):
        return f"{self.name} ({self.code})"
