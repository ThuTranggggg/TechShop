"""
Shipment Module - Django Admin Configuration

Admin panels for managing shipments, items, and tracking events.
"""

from django.contrib import admin
from django.utils.html import format_html

from modules.shipping.infrastructure.models import (
    ShipmentModel,
    ShipmentItemModel,
    ShipmentTrackingEventModel,
)


class ShipmentItemInline(admin.TabularInline):
    """Inline display of shipment items."""
    
    model = ShipmentItemModel
    fields = (
        "product_id", 
        "product_name_snapshot", 
        "sku", 
        "quantity"
    )
    readonly_fields = (
        "product_id", 
        "product_name_snapshot", 
        "sku", 
        "quantity"
    )
    extra = 0
    can_delete = False


class ShipmentTrackingEventInline(admin.TabularInline):
    """Inline display of tracking timeline."""
    
    model = ShipmentTrackingEventModel
    fields = (
        "event_type", 
        "status_after", 
        "location", 
        "event_time", 
        "description"
    )
    readonly_fields = (
        "event_type", 
        "status_after", 
        "location", 
        "event_time", 
        "description"
    )
    extra = 0
    can_delete = False


@admin.register(ShipmentModel)
class ShipmentAdmin(admin.ModelAdmin):
    """Admin panel for shipments."""
    
    list_display = (
        "shipment_reference",
        "tracking_number",
        "status_display",
        "order_number",
        "provider",
        "created_at",
    )
    
    search_fields = (
        "shipment_reference",
        "tracking_number",
        "order_id",
        "order_number",
    )
    
    list_filter = (
        "status",
        "provider",
        "service_level",
        "created_at",
    )
    
    readonly_fields = (
        "id",
        "shipment_reference",
        "tracking_number",
        "created_at",
        "updated_at",
    )
    
    fieldsets = (
        (
            "Basic Info",
            {
                "fields": (
                    "id",
                    "shipment_reference",
                    "tracking_number",
                    "order_id",
                    "order_number",
                    "user_id",
                )
            },
        ),
        (
            "Status & Timeline",
            {
                "fields": (
                    "status",
                    "created_at",
                    "updated_at",
                )
            },
        ),
        (
            "Receiver Address",
            {
                "fields": (
                    "receiver_name",
                    "receiver_phone",
                    "address_line1",
                    "address_line2",
                    "ward",
                    "district",
                    "city",
                    "country",
                    "postal_code",
                )
            },
        ),
        (
            "Shipment Details",
            {
                "fields": (
                    "package_count",
                    "package_weight",
                    "service_level",
                )
            },
        ),
        (
            "Provider Info",
            {
                "fields": (
                    "provider",
                    "carrier_shipment_id",
                )
            },
        ),
        (
            "Delivery Info",
            {
                "fields": (
                    "expected_pickup_at",
                    "expected_delivery_at",
                    "shipped_at",
                    "delivered_at",
                    "cancelled_at",
                    "failure_reason",
                )
            },
        ),
        (
            "Costs",
            {
                "fields": (
                    "shipping_fee_amount",
                    "currency",
                )
            },
        ),
    )
    
    inlines = (ShipmentItemInline, ShipmentTrackingEventInline)
    
    def status_display(self, obj):
        """Color-coded status display."""
        colors = {
            "CREATED": "#808080",
            "PENDING_PICKUP": "#FFA500",
            "PICKED_UP": "#87CEEB",
            "IN_TRANSIT": "#4169E1",
            "OUT_FOR_DELIVERY": "#1E90FF",
            "DELIVERED": "#228B22",
            "FAILED_DELIVERY": "#DC143C",
            "RETURNED": "#8B008B",
            "CANCELLED": "#696969",
        }
        color = colors.get(obj.status, "#000000")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )
    
    status_display.short_description = "Status"
    
    def has_add_permission(self, request):
        """Prevent adding shipments from admin (must use API)."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deleting shipments (audit trail)."""
        return False
    
    def get_readonly_fields(self, request, obj=None):
        """Most fields are read-only in admin."""
        if obj:
            return self.readonly_fields + [
                "shipment_reference",
                "tracking_number",
                "order_id",
                "order_number",
                "user_id",
                "status",
            ]
        return self.readonly_fields


@admin.register(ShipmentItemModel)
class ShipmentItemAdmin(admin.ModelAdmin):
    """Admin panel for shipment items."""
    
    list_display = (
        "product_id",
        "product_name_snapshot",
        "sku",
        "quantity",
        "shipment_reference",
    )
    
    search_fields = (
        "product_id",
        "product_name_snapshot",
        "sku",
        "shipment__shipment_reference",
    )
    
    list_filter = (
        "created_at",
    )
    
    readonly_fields = (
        "shipment",
        "product_id",
        "product_name_snapshot",
        "sku",
        "quantity",
        "created_at",
    )
    
    fieldsets = (
        (
            "Item Details",
            {
                "fields": (
                    "shipment",
                    "product_id",
                    "product_name_snapshot",
                    "variant_name_snapshot",
                    "sku",
                )
            },
        ),
        (
            "Quantity",
            {
                "fields": (
                    "quantity",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "created_at",
                )
            },
        ),
    )
    
    def shipment_reference(self, obj):
        """Display shipment reference."""
        return obj.shipment.shipment_reference
    
    shipment_reference.short_description = "Shipment Reference"
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ShipmentTrackingEventModel)
class ShipmentTrackingEventAdmin(admin.ModelAdmin):
    """Admin panel for tracking events (read-only timeline)."""
    
    list_display = (
        "event_type_display",
        "status_after_display",
        "location",
        "event_time",
        "shipment_reference",
    )
    
    search_fields = (
        "shipment__shipment_reference",
        "location",
        "description",
    )
    
    list_filter = (
        "event_type",
        "created_at",
    )
    
    readonly_fields = (
        "shipment",
        "event_type",
        "status_before",
        "status_after",
        "event_time",
        "location",
        "description",
        "created_at",
    )
    
    fieldsets = (
        (
            "Event Info",
            {
                "fields": (
                    "shipment",
                    "event_type",
                    "status_before",
                    "status_after",
                )
            },
        ),
        (
            "Location & Time",
            {
                "fields": (
                    "location",
                    "event_time",
                )
            },
        ),
        (
            "Details",
            {
                "fields": (
                    "description",
                    "provider_event_id",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "created_at",
                )
            },
        ),
    )
    
    def event_type_display(self, obj):
        """Display event type."""
        return obj.get_event_type_display()
    
    event_type_display.short_description = "Event Type"
    
    def status_after_display(self, obj):
        """Color-coded status display."""
        colors = {
            "CREATED": "#808080",
            "PENDING_PICKUP": "#FFA500",
            "PICKED_UP": "#87CEEB",
            "IN_TRANSIT": "#4169E1",
            "OUT_FOR_DELIVERY": "#1E90FF",
            "DELIVERED": "#228B22",
            "FAILED_DELIVERY": "#DC143C",
            "RETURNED": "#8B008B",
            "CANCELLED": "#696969",
        }
        color = colors.get(obj.status_after, "#000000")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_after_display() if obj.status_after else "—",
        )
    
    status_after_display.short_description = "Status After"
    
    def shipment_reference(self, obj):
        """Display shipment reference."""
        return obj.shipment.shipment_reference
    
    shipment_reference.short_description = "Shipment Reference"
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
