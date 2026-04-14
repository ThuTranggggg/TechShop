"""
Shipment Domain Layer

Core business logic and domain models.
"""

from .entities import (
    Shipment,
    ShipmentStatus,
    ShipmentTrackingEvent,
    ShipmentTrackingEventType,
    ShipmentItemSnapshot,
    ReceiverAddress,
    ShippingProvider,
    ShippingServiceLevel,
    Money,
)
from .repositories import ShipmentRepository, ShipmentTrackingEventRepository
from .services import ShipmentValidator, ShipmentFactory, ShipmentStateService
from .value_objects import (
    TrackingStatus,
    TrackingInfo,
    ShippingMetadata,
    CarrierReference,
    ShippingCost,
    ExpectedDeliveryWindow,
)

__all__ = [
    "Shipment",
    "ShipmentStatus",
    "ShipmentTrackingEvent",
    "ShipmentTrackingEventType",
    "ShipmentItemSnapshot",
    "ReceiverAddress",
    "ShippingProvider",
    "ShippingServiceLevel",
    "Money",
    "ShipmentRepository",
    "ShipmentTrackingEventRepository",
    "ShipmentValidator",
    "ShipmentFactory",
    "ShipmentStateService",
    "TrackingStatus",
    "TrackingInfo",
    "ShippingMetadata",
    "CarrierReference",
    "ShippingCost",
    "ExpectedDeliveryWindow",
]
