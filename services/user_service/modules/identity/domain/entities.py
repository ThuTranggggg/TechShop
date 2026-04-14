"""
Domain entities for Identity context.

Business logic and rules for User and Address entities.
"""
from typing import Optional
from datetime import datetime
from .enums import UserRole, AddressType


class User:
    """
    User domain entity.
    
    Represents a user in the system with their profile and business rules.
    """
    
    def __init__(
        self,
        id: Optional[str] = None,
        email: str = "",
        full_name: str = "",
        phone_number: Optional[str] = None,
        date_of_birth: Optional[datetime] = None,
        avatar_url: Optional[str] = None,
        role: UserRole = UserRole.CUSTOMER,
        is_active: bool = True,
        is_verified: bool = False,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        last_login: Optional[datetime] = None,
    ):
        self.id = id
        self.email = email
        self.full_name = full_name
        self.phone_number = phone_number
        self.date_of_birth = date_of_birth
        self.avatar_url = avatar_url
        self.role = role
        self.is_active = is_active
        self.is_verified = is_verified
        self.created_at = created_at
        self.updated_at = updated_at
        self.last_login = last_login
    
    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.role == UserRole.ADMIN
    
    def is_staff(self) -> bool:
        """Check if user is staff."""
        return self.role == UserRole.STAFF
    
    def is_customer(self) -> bool:
        """Check if user is customer."""
        return self.role == UserRole.CUSTOMER
    
    def can_manage_users(self) -> bool:
        """Check if user can manage other users (staff or admin only)."""
        return self.role in (UserRole.ADMIN, UserRole.STAFF)
    
    def can_promote_to_admin(self) -> bool:
        """Check if user can promote others to admin (admin only)."""
        return self.is_admin()
    
    def can_change_role_of(self, target_role: UserRole) -> bool:
        """Check if user can assign a specific role."""
        if not self.can_manage_users():
            return False
        
        if target_role == UserRole.ADMIN:
            return self.is_admin()
        
        return True
    
    def can_deactivate(self) -> bool:
        """Check if user account can be deactivated."""
        return self.is_active
    
    def can_activate(self) -> bool:
        """Check if user account can be activated."""
        return not self.is_active


class Address:
    """
    Address domain entity.
    
    Represents a user's address with business rules.
    """
    
    def __init__(
        self,
        id: Optional[str] = None,
        user_id: Optional[str] = None,
        receiver_name: str = "",
        phone_number: str = "",
        line1: str = "",
        line2: Optional[str] = None,
        ward: Optional[str] = None,
        district: str = "",
        city: str = "",
        country: str = "",
        postal_code: Optional[str] = None,
        address_type: AddressType = AddressType.HOME,
        is_default: bool = False,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.user_id = user_id
        self.receiver_name = receiver_name
        self.phone_number = phone_number
        self.line1 = line1
        self.line2 = line2
        self.ward = ward
        self.district = district
        self.city = city
        self.country = country
        self.postal_code = postal_code
        self.address_type = address_type
        self.is_default = is_default
        self.created_at = created_at
        self.updated_at = updated_at
    
    def full_address(self) -> str:
        """Get full address as a single string."""
        parts = [self.line1]
        if self.line2:
            parts.append(self.line2)
        if self.ward:
            parts.append(self.ward)
        parts.extend([self.district, self.city, self.country])
        if self.postal_code:
            parts.append(self.postal_code)
        
        return ", ".join(filter(None, parts))
