"""
Django models for Identity module.

This file re-exports models from the infrastructure layer so Django can discover them.
"""

from .infrastructure.models import (
    CustomUserManager,
    User,
    Address,
)

__all__ = [
    "CustomUserManager",
    "User",
    "Address",
]
