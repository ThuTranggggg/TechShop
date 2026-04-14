"""
Django app configuration for order module.
"""

from django.apps import AppConfig


class OrderConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.order"
    verbose_name = "Order Service"
    
    def ready(self):
        """Initialize app."""
        # Can import signals here if needed
        pass
