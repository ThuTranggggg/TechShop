"""
Shipping Service - Django App Configuration
"""

from django.apps import AppConfig


class ShippingConfig(AppConfig):
    """Configuration for the shipping service application."""
    
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.shipping"
    verbose_name = "Shipping Service"
    
    def ready(self):
        """Initialize app when Django starts."""
        # Import admin configuration
        from modules.shipping.presentation import admin  # noqa: F401
