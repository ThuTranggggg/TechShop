"""
Shipment Domain Value Objects

Immutable value objects for shipping domain.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional


class TrackingStatus(str, Enum):
    """Status for external tracking representation"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DELIVERED = "delivered"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class TrackingInfo:
    """
    External tracking information
    
    This is what we expose to customers via tracking URL.
    """
    tracking_number: str
    tracking_url: str
    status: TrackingStatus
    last_update: Optional[str] = None
    expected_delivery: Optional[str] = None
    current_location: Optional[str] = None


@dataclass
class ShippingMetadata:
    """Metadata for shipment"""
    # Additional fields that don't fit elsewhere
    data: dict

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    def set(self, key: str, value):
        self.data[key] = value


@dataclass
class CarrierReference:
    """
    Reference to carrier system
    
    Used to map between shipping_service and external carrier.
    """
    provider: str
    carrier_shipment_id: str
    carrier_tracking_url: Optional[str] = None
    raw_provider_data: dict = None

    def __post_init__(self):
        if self.raw_provider_data is None:
            self.raw_provider_data = {}


@dataclass
class ShippingCost:
    """
    Shipping cost information
    """
    amount: Decimal
    currency: str = "VND"
    breakdown: Optional[dict] = None  # e.g., {"base": 5000, "surcharge": 1000}

    def __post_init__(self):
        if self.breakdown is None:
            self.breakdown = {}

    def __str__(self) -> str:
        return f"{self.amount} {self.currency}"


@dataclass
class ExpectedDeliveryWindow:
    """
    Expected delivery window
    """
    min_days: int
    max_days: int
    service_level: str

    def __str__(self) -> str:
        if self.min_days == self.max_days:
            return f"{self.min_days} day(s)"
        return f"{self.min_days}-{self.max_days} days"
