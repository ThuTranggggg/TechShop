"""
Django app configuration for Inventory service.
"""
from django.apps import AppConfig


class InventoryConfig(AppConfig):
    """App config for inventory module."""
    
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.inventory"
    verbose_name = "Inventory Management"
