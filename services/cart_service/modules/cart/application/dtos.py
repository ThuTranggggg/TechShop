"""
Data Transfer Objects (DTOs) for Cart application layer.

DTOs transfer data between layers and services.
"""
from typing import Optional, Dict, List, Any
from decimal import Decimal
from dataclasses import dataclass, field
from datetime import datetime


# ===== Request/Command DTOs =====

@dataclass
class AddItemToCartDTO:
    """Request to add item to cart."""
    user_id: str
    product_id: str
    quantity: int
    variant_id: Optional[str] = None


@dataclass
class UpdateCartItemQuantityDTO:
    """Request to update cart item quantity."""
    user_id: str
    item_id: str
    new_quantity: int


@dataclass
class RemoveCartItemDTO:
    """Request to remove item from cart."""
    user_id: str
    item_id: str


@dataclass
class IncreaseCartItemQuantityDTO:
    """Request to increase item quantity."""
    user_id: str
    item_id: str
    increment: int = 1


@dataclass
class DecreaseCartItemQuantityDTO:
    """Request to decrease item quantity."""
    user_id: str
    item_id: str
    decrement: int = 1


@dataclass
class ClearCartDTO:
    """Request to clear cart."""
    user_id: str


@dataclass
class ValidateCartDTO:
    """Request to validate cart."""
    user_id: str


@dataclass
class RefreshCartDTO:
    """Request to refresh cart snapshots."""
    user_id: str


@dataclass
class CheckoutPreviewDTO:
    """Request to preview checkout."""
    user_id: str


@dataclass
class MarkCheckedOutDTO:
    """Request to mark cart as checked out (internal)."""
    cart_id: str


# ===== Response/View DTOs =====

@dataclass
class CartItemResponseDTO:
    """Response DTO for a cart item."""
    id: str
    product_id: str
    variant_id: Optional[str]
    product_name: str
    product_slug: str
    variant_name: Optional[str]
    brand_name: Optional[str]
    category_name: Optional[str]
    sku: Optional[str]
    thumbnail_url: Optional[str]
    quantity: int
    unit_price: str  # Decimal as string
    currency: str
    line_total: str  # Decimal as string
    status: str
    availability_checked_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "product_id": self.product_id,
            "variant_id": self.variant_id,
            "product_name": self.product_name,
            "product_slug": self.product_slug,
            "variant_name": self.variant_name,
            "brand_name": self.brand_name,
            "category_name": self.category_name,
            "sku": self.sku,
            "thumbnail_url": self.thumbnail_url,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "currency": self.currency,
            "line_total": self.line_total,
            "status": self.status,
            "availability_checked_at": self.availability_checked_at,
        }


@dataclass
class CartResponseDTO:
    """Response DTO for a cart."""
    id: str
    user_id: str
    status: str
    currency: str
    subtotal_amount: str
    total_quantity: int
    item_count: int
    items: List[CartItemResponseDTO] = field(default_factory=list)
    last_activity_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "status": self.status,
            "currency": self.currency,
            "subtotal_amount": self.subtotal_amount,
            "total_quantity": self.total_quantity,
            "item_count": self.item_count,
            "items": [item.to_dict() for item in self.items],
            "last_activity_at": self.last_activity_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class CartValidationIssueDTO:
    """Response DTO for a validation issue."""
    item_id: Optional[str]
    product_id: str
    status: str
    message: str


@dataclass
class CartValidationResultDTO:
    """Response DTO for cart validation."""
    is_valid: bool
    issues: List[CartValidationIssueDTO] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "issues": [
                {
                    "item_id": issue.item_id,
                    "product_id": issue.product_id,
                    "status": issue.status,
                    "message": issue.message,
                }
                for issue in self.issues
            ],
        }


@dataclass
class CheckoutPreviewDTO:
    """Response DTO for checkout preview."""
    is_valid: bool
    cart: CartResponseDTO
    issues: List[CartValidationIssueDTO] = field(default_factory=list)
    checkout_payload: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        payload = {
            "is_valid": self.is_valid,
            "cart": self.cart.to_dict(),
            "issues": [
                {
                    "item_id": issue.item_id,
                    "product_id": issue.product_id,
                    "status": issue.status,
                    "message": issue.message,
                }
                for issue in self.issues
            ],
        }
        if self.checkout_payload:
            payload["checkout_payload"] = self.checkout_payload
        return payload


# ===== Internal DTOs =====

@dataclass
class GetOrCreateActiveCartDTO:
    """Request to get or create active cart (internal)."""
    user_id: str


@dataclass
class GetActiveCartDTO:
    """Request to get active cart (internal)."""
    user_id: str


@dataclass
class GetCartDTO:
    """Request to get specific cart (internal)."""
    cart_id: str
