"""
Payment Module Django Configuration
"""

from django.apps import AppConfig


class PaymentConfig(AppConfig):
    """Configuration for Payment Module"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.payment"
    verbose_name = "Payment Module"
