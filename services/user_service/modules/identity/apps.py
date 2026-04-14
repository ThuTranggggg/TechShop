"""
App configuration for Identity module.
"""
from django.apps import AppConfig


class IdentityConfig(AppConfig):
    """Configuration for Identity module."""
    
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.identity"
    verbose_name = "Identity & User Management"
