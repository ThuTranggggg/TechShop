"""
Django app configuration for AI module.
"""
from django.apps import AppConfig


class AIConfig(AppConfig):
    """Django app for AI/recommendation service."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.ai"
    label = "ai"
    verbose_name = "AI Service"
