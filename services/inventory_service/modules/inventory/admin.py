"""
Django admin configuration for Inventory module.
"""
from django.contrib import admin
from django.utils.html import format_html

from .infrastructure.models import (
    StockItemModel,
    StockReservationModel,
    StockMovementModel,
    WarehouseModel,
)


@admin.register(StockItemModel)
class StockItemAdmin(admin.ModelAdmin):
    """Admin for StockItem model."""
    
    list_display = (
        "product_id",
        "warehouse_code",
        "on_hand_quantity",
        "reserved_quantity",
        "available_quantity_display",
        "is_low_stock_display",
        "is_active",
    )
    
    list_filter = ("is_active", "warehouse_code", "updated_at")
    search_fields = ("product_id", "sku", "warehouse_code")
    
    fieldsets = (
        ("Product Reference", {
            "fields": ("product_id", "variant_id", "sku"),
        }),
        ("Location", {
            "fields": ("warehouse_code",),
        }),
        ("Stock Levels", {
            "fields": ("on_hand_quantity", "reserved_quantity", "safety_stock"),
            "description": "on_hand + reserved must not exceed on_hand",
        }),
        ("Status", {
            "fields": ("is_active",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )
    
    readonly_fields = ("created_at", "updated_at")
    
    def available_quantity_display(self, obj):
        """Display available quantity with color."""
        if obj.available_quantity < 0:
            color = "#FF0000"  # Red
        elif obj.available_quantity == 0:
            color = "#FFA500"  # Orange
        else:
            color = "#008000"  # Green
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.available_quantity,
        )
    
    available_quantity_display.short_description = "Available Qty"
    
    def is_low_stock_display(self, obj):
        """Display low stock status."""
        if obj.is_low_stock():
            return format_html(
                '<span style="color: #FFA500; font-weight: bold;">LOW</span>'
            )
        return "OK"
    
    is_low_stock_display.short_description = "Stock Status"


@admin.register(StockReservationModel)
class StockReservationAdmin(admin.ModelAdmin):
    """Admin for StockReservation model."""
    
    list_display = (
        "reservation_code",
        "product_id",
        "quantity",
        "status",
        "order_id",
        "cart_id",
        "expires_at",
    )
    
    list_filter = ("status", "expires_at", "created_at")
    search_fields = ("reservation_code", "product_id", "order_id", "cart_id")
    
    fieldsets = (
        ("Reservation Details", {
            "fields": ("reservation_code", "stock_item", "status"),
        }),
        ("Product Reference", {
            "fields": ("product_id", "variant_id"),
        }),
        ("Order/Cart Reference", {
            "fields": ("order_id", "cart_id", "user_id"),
        }),
        ("Quantity", {
            "fields": ("quantity",),
        }),
        ("Expiration", {
            "fields": ("expires_at",),
        }),
        ("Additional Data", {
            "fields": ("metadata",),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )
    
    readonly_fields = ("created_at", "updated_at", "reservation_code")


@admin.register(StockMovementModel)
class StockMovementAdmin(admin.ModelAdmin):
    """Admin for StockMovement model."""
    
    list_display = (
        "created_at",
        "stock_item",
        "movement_type",
        "quantity",
        "reference_type",
        "reference_id",
    )
    
    list_filter = ("movement_type", "created_at", "reference_type")
    search_fields = ("stock_item__product_id", "reference_id", "product_id")
    
    fieldsets = (
        ("Stock Reference", {
            "fields": ("stock_item", "product_id", "variant_id"),
        }),
        ("Movement Details", {
            "fields": ("movement_type", "quantity"),
        }),
        ("Reference", {
            "fields": ("reference_type", "reference_id"),
        }),
        ("Notes", {
            "fields": ("note", "created_by"),
        }),
        ("Additional Data", {
            "fields": ("metadata",),
            "classes": ("collapse",),
        }),
        ("Timestamp", {
            "fields": ("created_at",),
            "classes": ("collapse",),
        }),
    )
    
    readonly_fields = ("created_at", "stock_item", "movement_type", "quantity")
    
    def has_add_permission(self, request):
        """Prevent manual creation of movements."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of movements."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent editing of movements."""
        return False


@admin.register(WarehouseModel)
class WarehouseAdmin(admin.ModelAdmin):
    """Admin for Warehouse model."""
    
    list_display = ("code", "name", "warehouse_type", "location", "is_active")
    list_filter = ("is_active", "warehouse_type", "created_at")
    search_fields = ("code", "name", "location")
    
    fieldsets = (
        ("Basic Info", {
            "fields": ("code", "name", "warehouse_type"),
        }),
        ("Location", {
            "fields": ("location",),
        }),
        ("Status", {
            "fields": ("is_active",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )
    
    readonly_fields = ("created_at", "updated_at")
