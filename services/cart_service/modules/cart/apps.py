"""
App configuration for Cart module.
"""
from django.apps import AppConfig


class CartConfig(AppConfig):
    """Configuration for cart module."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.cart'
    verbose_name = 'Cart Service'
