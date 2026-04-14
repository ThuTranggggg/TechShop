"""
Domain enums for Identity context.

Defines enumerated types for user roles, address types, and verification status.
"""
from enum import Enum


class UserRole(str, Enum):
    """User roles in the system."""
    
    CUSTOMER = "customer"
    STAFF = "staff"
    ADMIN = "admin"
    
    @classmethod
    def choices(cls):
        """Return choices for Django model field."""
        return [(role.value, role.name) for role in cls]
    
    @classmethod
    def public_roles(cls):
        """Roles that non-admin can register with."""
        return [cls.CUSTOMER]


class AddressType(str, Enum):
    """Address type classification."""
    
    HOME = "home"
    OFFICE = "office"
    OTHER = "other"
    
    @classmethod
    def choices(cls):
        """Return choices for Django model field."""
        return [(addr_type.value, addr_type.name) for addr_type in cls]


class VerificationStatus(str, Enum):
    """Email verification status."""
    
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    PENDING = "pending"
    
    @classmethod
    def choices(cls):
        """Return choices for Django model field."""
        return [(status.value, status.name) for status in cls]
