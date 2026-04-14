"""
Django admin configuration for Cart module models.
"""
from django.contrib import admin

from .infrastructure.models import CartModel, CartItemModel


@admin.register(CartModel)
class CartAdmin(admin.ModelAdmin):
    """Admin interface for Cart model."""
    
    list_display = [
        "id",
        "user_id",
        "status",
        "item_count",
        "total_quantity",
        "subtotal_amount",
        "currency",
        "updated_at",
    ]
    list_filter = ["status", "currency", "created_at", "updated_at"]
    search_fields = ["user_id"]
    readonly_fields = ["id", "created_at", "updated_at"]
    
    fieldsets = (
        ("Cart Info", {
            "fields": ("id", "user_id", "status", "currency")
        }),
        ("Totals", {
            "fields": ("subtotal_amount", "total_quantity", "item_count")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at", "last_activity_at"),
            "classes": ("collapse",)
        }),
    )
    
    def has_add_permission(self, request):
        """Prevent adding carts from admin."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deleting carts from admin."""
        return False


@admin.register(CartItemModel)
class CartItemAdmin(admin.ModelAdmin):
    """Admin interface for CartItem model."""
    
    list_display = [
        "id",
        "cart",
        "product_name_snapshot",
        "quantity",
        "unit_price_snapshot",
        "status",
        "created_at",
    ]
    list_filter = ["status", "currency", "created_at", "updated_at"]
    search_fields = ["product_name_snapshot", "product_id", "cart__user_id"]
    readonly_fields = ["id", "created_at", "updated_at"]
    
    fieldsets = (
        ("Cart Item Info", {
            "fields": ("id", "cart", "product_id", "variant_id")
        }),
        ("Product Snapshot", {
            "fields": (
                "product_name_snapshot",
                "product_slug_snapshot",
                "variant_name_snapshot",
                "brand_name_snapshot",
                "category_name_snapshot",
                "sku",
                "thumbnail_url_snapshot",
            ),
            "classes": ("collapse",)
        }),
        ("Quantity & Price", {
            "fields": ("quantity", "unit_price_snapshot", "currency")
        }),
        ("Attributes", {
            "fields": ("attributes_snapshot",),
            "classes": ("collapse",)
        }),
        ("Availability", {
            "fields": ("status", "availability_checked_at"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    
    def has_add_permission(self, request):
        """Prevent adding items from admin."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deleting items from admin."""
        return False
