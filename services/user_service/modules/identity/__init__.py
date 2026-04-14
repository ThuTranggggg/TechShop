"""
Identity and Authentication module.

Provides user authentication, role-based access control, and account management.
"""
from django.apps import apps

default_app_config = "modules.identity.apps.IdentityConfig"

def get_user_model():
    """Get the User model for this module."""
    return apps.get_model("identity", "User", require_ready=False)
