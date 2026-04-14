"""
Application layer DTO (Data Transfer Objects).

Used for transferring data between presentation and application layers.
"""
from dataclasses import dataclass, asdict
from typing import Optional
from decimal import Decimal


@dataclass
class ProductReferenceDTO:
    """DTO for product reference."""
    product_id: str
    variant_id: Optional[str] = None
    sku: Optional[str] = None


@dataclass
class StockItemDTO:
    """DTO for stock item."""
    id: str
    product_id: str
    variant_id: Optional[str]
    sku: Optional[str]
    warehouse_code: str
    on_hand_quantity: int
    reserved_quantity: int
    available_quantity: int
    safety_stock: int
    is_in_stock: bool
    is_low_stock: bool
    is_active: bool
    created_at: str
    updated_at: str


@dataclass
class CreateStockItemDTO:
    """DTO for creating stock item."""
    product_id: str
    variant_id: Optional[str] = None
    sku: Optional[str] = None
    warehouse_code: str = "MAIN"
    on_hand_quantity: int = 0
    safety_stock: int = 0


@dataclass
class UpdateStockItemDTO:
    """DTO for updating stock item."""
    safety_stock: Optional[int] = None
    is_active: Optional[bool] = None


@dataclass
class StockInDTO:
    """DTO for stock in operation."""
    quantity: int
    reference_id: Optional[str] = None
    note: Optional[str] = None


@dataclass
class StockOutDTO:
    """DTO for stock out operation."""
    quantity: int
    reference_id: Optional[str] = None
    note: Optional[str] = None


@dataclass
class AdjustStockDTO:
    """DTO for stock adjustment."""
    quantity: int  # Can be positive or negative
    reason: str


@dataclass
class StockMovementDTO:
    """DTO for stock movement."""
    id: str
    stock_item_id: str
    product_id: str
    variant_id: Optional[str]
    movement_type: str
    quantity: int
    reference_type: Optional[str]
    reference_id: Optional[str]
    note: Optional[str]
    created_by: Optional[str]
    created_at: str


@dataclass
class StockReservationDTO:
    """DTO for stock reservation."""
    id: str
    reservation_code: str
    product_id: str
    variant_id: Optional[str]
    quantity: int
    status: str
    order_id: Optional[str]
    cart_id: Optional[str]
    user_id: Optional[str]
    expires_at: str
    created_at: str
    updated_at: str


@dataclass
class CreateReservationDTO:
    """
    DTO for creating reservation.
    
    ISSUE FIX #4: expires_in_minutes now defaults to configurable timeout.
    Previously hardcoded to 60 minutes (too short for checkout + payment).
    Now uses STOCK_RESERVATION_TIMEOUT_MINUTES from settings (default 180 = 3 hours).
    """
    product_id: str
    variant_id: Optional[str] = None
    quantity: int = 1
    order_id: Optional[str] = None
    cart_id: Optional[str] = None
    user_id: Optional[str] = None
    # ISSUE FIX #4: Use config value as default (180 minutes = 3 hours)
    # Can be overridden via env var STOCK_RESERVATION_TIMEOUT_MINUTES
    expires_in_minutes: int = None  # Will be set from config in presentation layer
    
    def __post_init__(self):
        """Apply config default if not already set."""
        if self.expires_in_minutes is None:
            from django.conf import settings
            self.expires_in_minutes = getattr(
                settings,
                "STOCK_RESERVATION_TIMEOUT_MINUTES",
                180  # Fallback: 3 hours
            )


@dataclass
class CheckAvailabilityItemDTO:
    """DTO for a single item in availability check."""
    product_id: str
    variant_id: Optional[str] = None
    quantity: int = 1


@dataclass
class CheckAvailabilityDTO:
    """DTO for checking availability."""
    items: list  # List of CheckAvailabilityItemDTO


@dataclass
class AvailabilityResultDTO:
    """DTO for availability check result."""
    product_id: str
    variant_id: Optional[str]
    requested_quantity: int
    available_quantity: int
    can_reserve: bool
    is_in_stock: bool
    stock_item_id: Optional[str] = None


@dataclass
class InventorySummaryDTO:
    """DTO for inventory summary."""
    product_id: str
    variant_id: Optional[str]
    total_on_hand: int
    total_reserved: int
    total_available: int
    warehouses: list  # List of warehouse-specific data
