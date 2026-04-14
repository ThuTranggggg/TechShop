"""
Django admin configuration for order module.
"""

from django.contrib import admin
from .infrastructure.models import (
    OrderModel, OrderItemModel, OrderStatusHistoryModel
)


@admin.register(OrderModel)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number", "user_id", "status", "payment_status", "fulfillment_status",
        "grand_total_amount", "currency", "placed_at", "created_at"
    )
    list_filter = (
        "status", "payment_status", "fulfillment_status", "currency", "created_at", "placed_at"
    )
    search_fields = (
        "order_number", "user_id", "payment_reference", "shipment_reference",
        "customer_email_snapshot"
    )
    readonly_fields = (
        "id", "created_at", "updated_at"
    )
    fieldsets = (
        ("Basic Info", {
            "fields": ("id", "order_number", "user_id", "cart_id", "created_at", "updated_at")
        }),
        ("Status", {
            "fields": ("status", "payment_status", "fulfillment_status", "placed_at", "paid_at", "cancelled_at", "completed_at")
        }),
        ("Pricing", {
            "fields": (
                "currency", "subtotal_amount", "shipping_fee_amount", "discount_amount",
                "tax_amount", "grand_total_amount", "total_quantity", "item_count"
            )
        }),
        ("Customer", {
            "fields": (
                "customer_name_snapshot", "customer_email_snapshot", "customer_phone_snapshot"
            )
        }),
        ("Shipping Address", {
            "fields": (
                "receiver_name", "receiver_phone", "shipping_line1", "shipping_line2",
                "shipping_ward", "shipping_district", "shipping_city", "shipping_country",
                "shipping_postal_code"
            )
        }),
        ("References", {
            "fields": (
                "payment_id", "payment_reference", "shipment_id", "shipment_reference",
                "stock_reservation_refs"
            )
        }),
        ("Notes", {
            "fields": ("notes",)
        }),
    )
    ordering = ["-created_at"]


@admin.register(OrderItemModel)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "id", "order", "product_name_snapshot", "sku", "quantity", "unit_price",
        "line_total", "currency"
    )
    list_filter = ("currency", "created_at")
    search_fields = ("order__order_number", "product_name_snapshot", "sku", "product_id")
    readonly_fields = ("id", "created_at", "updated_at", "line_total")
    fieldsets = (
        ("Basic Info", {
            "fields": ("id", "order", "created_at", "updated_at")
        }),
        ("Product Reference", {
            "fields": ("product_id", "variant_id", "sku")
        }),
        ("Pricing", {
            "fields": ("quantity", "unit_price", "line_total", "currency")
        }),
        ("Product Snapshot", {
            "fields": (
                "product_name_snapshot", "product_slug_snapshot", "variant_name_snapshot",
                "brand_name_snapshot", "category_name_snapshot", "thumbnail_url_snapshot"
            )
        }),
        ("Attributes", {
            "fields": ("attributes_snapshot",)
        }),
    )
    ordering = ["-created_at"]


@admin.register(OrderStatusHistoryModel)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "order", "from_status", "to_status", "changed_by", "created_at"
    )
    list_filter = ("to_status", "from_status", "created_at")
    search_fields = ("order__order_number", "note")
    readonly_fields = ("id", "created_at")
    fieldsets = (
        ("Transition", {
            "fields": ("id", "order", "from_status", "to_status", "changed_by", "created_at")
        }),
        ("Details", {
            "fields": ("note", "metadata")
        }),
    )
    ordering = ["-created_at"]
