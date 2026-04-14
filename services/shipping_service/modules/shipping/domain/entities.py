"""
Shipment Domain Entities

Core aggregate roots and entities for shipping domain.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4


class ShipmentStatus(str, Enum):
    """Valid shipment statuses"""
    CREATED = "created"
    PENDING_PICKUP = "pending_pickup"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    FAILED_DELIVERY = "failed_delivery"
    RETURNED = "returned"
    CANCELLED = "cancelled"


class ShipmentTrackingEventType(str, Enum):
    """Tracking event types"""
    SHIPMENT_CREATED = "shipment_created"
    PICKUP_SCHEDULED = "pickup_scheduled"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    FAILED_DELIVERY = "failed_delivery"
    RETURNED = "returned"
    CANCELLED = "cancelled"


class ShippingProvider(str, Enum):
    """Supported shipping providers"""
    MOCK = "mock"
    GIAO_HANG_NHANH = "ghn"
    GIAO_HANG_TIET_KIEM = "ghtk"
    VIETPOST = "vietpost"


class ShippingServiceLevel(str, Enum):
    """Shipping service levels"""
    STANDARD = "standard"
    EXPRESS = "express"
    OVERNIGHT = "overnight"


@dataclass
class Money:
    """Money value object"""
    amount: Decimal
    currency: str = "VND"

    def __str__(self) -> str:
        return f"{self.amount} {self.currency}"


@dataclass
class ReceiverAddress:
    """Receiver address snapshot"""
    name: str
    phone: str
    address_line1: str
    address_line2: Optional[str] = None
    ward: Optional[str] = None
    district: str = ""
    city: str = ""
    country: str = "VN"
    postal_code: Optional[str] = None

    def is_valid(self) -> bool:
        """Validate address"""
        return all([
            self.name.strip(),
            self.phone.strip(),
            self.address_line1.strip(),
            self.district.strip(),
            self.city.strip(),
        ])


@dataclass
class ShipmentItemSnapshot:
    """Snapshot of an item in shipment"""
    order_item_id: Optional[UUID]
    product_id: UUID
    variant_id: Optional[UUID]
    sku: Optional[str]
    quantity: int
    product_name_snapshot: str
    variant_name_snapshot: Optional[str] = None

    def is_valid(self) -> bool:
        """Validate item"""
        return (
            self.product_id is not None
            and self.quantity > 0
            and self.product_name_snapshot.strip()
        )


@dataclass
class ShipmentTrackingEvent:
    """Tracking event - immutable timeline record"""
    id: UUID
    shipment_id: UUID
    event_type: ShipmentTrackingEventType
    status_before: Optional[ShipmentStatus]
    status_after: ShipmentStatus
    description: Optional[str] = None
    location: Optional[str] = None
    provider_event_id: Optional[str] = None
    raw_payload: dict = field(default_factory=dict)
    event_time: datetime = field(default_factory=datetime.utcnow)
    created_at: datetime = field(default_factory=datetime.utcnow)

    @staticmethod
    def create_from_shipment(
        shipment_id: UUID,
        event_type: ShipmentTrackingEventType,
        status_before: Optional[ShipmentStatus],
        status_after: ShipmentStatus,
        description: Optional[str] = None,
        location: Optional[str] = None,
        provider_event_id: Optional[str] = None,
        raw_payload: Optional[dict] = None,
    ) -> "ShipmentTrackingEvent":
        """Factory method to create tracking event"""
        return ShipmentTrackingEvent(
            id=uuid4(),
            shipment_id=shipment_id,
            event_type=event_type,
            status_before=status_before,
            status_after=status_after,
            description=description,
            location=location,
            provider_event_id=provider_event_id,
            raw_payload=raw_payload or {},
        )


class Shipment:
    """
    Shipment Aggregate Root

    Represents a complete shipment lifecycle.
    Manages state transitions and tracks all events.
    """

    def __init__(
        self,
        id: UUID,
        order_id: UUID,
        order_number: str,
        user_id: Optional[UUID],
        shipment_reference: str,
        tracking_number: str,
        receiver_address: ReceiverAddress,
        items: List[ShipmentItemSnapshot],
        provider: ShippingProvider,
        service_level: ShippingServiceLevel,
        status: ShipmentStatus = ShipmentStatus.CREATED,
        tracking_url: Optional[str] = None,
        label_url: Optional[str] = None,
        package_count: int = 1,
        package_weight: Optional[Decimal] = None,
        shipping_fee: Optional[Money] = None,
        failure_reason: Optional[str] = None,
        carrier_shipment_id: Optional[str] = None,
        expected_pickup_at: Optional[datetime] = None,
        expected_delivery_at: Optional[datetime] = None,
        shipped_at: Optional[datetime] = None,
        delivered_at: Optional[datetime] = None,
        cancelled_at: Optional[datetime] = None,
        created_at: datetime = None,
        updated_at: datetime = None,
        metadata: Optional[dict] = None,
    ):
        self.id = id
        self.order_id = order_id
        self.order_number = order_number
        self.user_id = user_id
        self.shipment_reference = shipment_reference
        self.tracking_number = tracking_number
        self.receiver_address = receiver_address
        self.items = items
        self.provider = provider
        self.service_level = service_level
        self.status = status
        self.tracking_url = tracking_url
        self.label_url = label_url
        self.package_count = package_count
        self.package_weight = package_weight
        self.shipping_fee = shipping_fee
        self.failure_reason = failure_reason
        self.carrier_shipment_id = carrier_shipment_id
        self.expected_pickup_at = expected_pickup_at
        self.expected_delivery_at = expected_delivery_at
        self.shipped_at = shipped_at
        self.delivered_at = delivered_at
        self.cancelled_at = cancelled_at
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.metadata = metadata or {}
        self.tracking_events: List[ShipmentTrackingEvent] = []

    # ===== State Transition Methods =====

    def transition_to_pending_pickup(self, description: Optional[str] = None) -> ShipmentTrackingEvent:
        """Transition to pending_pickup"""
        if self.status not in (ShipmentStatus.CREATED,):
            raise ValueError(
                f"Cannot transition from {self.status.value} to pending_pickup"
            )
        event = ShipmentTrackingEvent.create_from_shipment(
            shipment_id=self.id,
            event_type=ShipmentTrackingEventType.PICKUP_SCHEDULED,
            status_before=self.status,
            status_after=ShipmentStatus.PENDING_PICKUP,
            description=description,
        )
        self.status = ShipmentStatus.PENDING_PICKUP
        self.tracking_events.append(event)
        self.updated_at = datetime.utcnow()
        return event

    def mark_picked_up(self, description: Optional[str] = None) -> ShipmentTrackingEvent:
        """Mark as picked up"""
        if self.status not in (ShipmentStatus.PENDING_PICKUP,):
            raise ValueError(
                f"Cannot mark picked up from {self.status.value}"
            )
        self.shipped_at = datetime.utcnow()
        event = ShipmentTrackingEvent.create_from_shipment(
            shipment_id=self.id,
            event_type=ShipmentTrackingEventType.PICKED_UP,
            status_before=self.status,
            status_after=ShipmentStatus.PICKED_UP,
            description=description,
        )
        self.status = ShipmentStatus.PICKED_UP
        self.tracking_events.append(event)
        self.updated_at = datetime.utcnow()
        return event

    def mark_in_transit(self, description: Optional[str] = None, location: Optional[str] = None) -> ShipmentTrackingEvent:
        """Mark as in transit"""
        if self.status not in (ShipmentStatus.PICKED_UP, ShipmentStatus.PENDING_PICKUP):
            raise ValueError(
                f"Cannot mark in transit from {self.status.value}"
            )
        event = ShipmentTrackingEvent.create_from_shipment(
            shipment_id=self.id,
            event_type=ShipmentTrackingEventType.IN_TRANSIT,
            status_before=self.status,
            status_after=ShipmentStatus.IN_TRANSIT,
            description=description,
            location=location,
        )
        self.status = ShipmentStatus.IN_TRANSIT
        self.tracking_events.append(event)
        self.updated_at = datetime.utcnow()
        return event

    def mark_out_for_delivery(self, description: Optional[str] = None, location: Optional[str] = None) -> ShipmentTrackingEvent:
        """Mark as out for delivery"""
        if self.status not in (ShipmentStatus.IN_TRANSIT,):
            raise ValueError(
                f"Cannot mark out for delivery from {self.status.value}"
            )
        event = ShipmentTrackingEvent.create_from_shipment(
            shipment_id=self.id,
            event_type=ShipmentTrackingEventType.OUT_FOR_DELIVERY,
            status_before=self.status,
            status_after=ShipmentStatus.OUT_FOR_DELIVERY,
            description=description,
            location=location,
        )
        self.status = ShipmentStatus.OUT_FOR_DELIVERY
        self.tracking_events.append(event)
        self.updated_at = datetime.utcnow()
        return event

    def mark_delivered(
        self,
        description: Optional[str] = None,
        location: Optional[str] = None,
    ) -> ShipmentTrackingEvent:
        """Mark as delivered"""
        if self.status not in (ShipmentStatus.OUT_FOR_DELIVERY,):
            raise ValueError(
                f"Cannot mark delivered from {self.status.value}"
            )
        self.delivered_at = datetime.utcnow()
        event = ShipmentTrackingEvent.create_from_shipment(
            shipment_id=self.id,
            event_type=ShipmentTrackingEventType.DELIVERED,
            status_before=self.status,
            status_after=ShipmentStatus.DELIVERED,
            description=description or "Delivered successfully",
            location=location,
        )
        self.status = ShipmentStatus.DELIVERED
        self.tracking_events.append(event)
        self.updated_at = datetime.utcnow()
        return event

    def mark_failed_delivery(
        self,
        reason: str,
        description: Optional[str] = None,
        location: Optional[str] = None,
    ) -> ShipmentTrackingEvent:
        """Mark delivery as failed"""
        if self.status not in (ShipmentStatus.OUT_FOR_DELIVERY, ShipmentStatus.IN_TRANSIT):
            raise ValueError(
                f"Cannot mark failed delivery from {self.status.value}"
            )
        self.failure_reason = reason
        event = ShipmentTrackingEvent.create_from_shipment(
            shipment_id=self.id,
            event_type=ShipmentTrackingEventType.FAILED_DELIVERY,
            status_before=self.status,
            status_after=ShipmentStatus.FAILED_DELIVERY,
            description=description or f"Delivery failed: {reason}",
            location=location,
        )
        self.status = ShipmentStatus.FAILED_DELIVERY
        self.tracking_events.append(event)
        self.updated_at = datetime.utcnow()
        return event

    def mark_returned(
        self,
        description: Optional[str] = None,
        location: Optional[str] = None,
    ) -> ShipmentTrackingEvent:
        """Mark shipment as returned"""
        if self.status not in (ShipmentStatus.FAILED_DELIVERY,):
            raise ValueError(
                f"Cannot mark returned from {self.status.value}"
            )
        event = ShipmentTrackingEvent.create_from_shipment(
            shipment_id=self.id,
            event_type=ShipmentTrackingEventType.RETURNED,
            status_before=self.status,
            status_after=ShipmentStatus.RETURNED,
            description=description or "Shipment returned to sender",
            location=location,
        )
        self.status = ShipmentStatus.RETURNED
        self.tracking_events.append(event)
        self.updated_at = datetime.utcnow()
        return event

    def cancel(self, reason: Optional[str] = None) -> ShipmentTrackingEvent:
        """Cancel shipment"""
        # Can only cancel from certain states
        if self.status in (ShipmentStatus.DELIVERED, ShipmentStatus.RETURNED):
            raise ValueError(
                f"Cannot cancel shipment in status {self.status.value}"
            )
        self.cancelled_at = datetime.utcnow()
        self.failure_reason = reason or "Cancelled"
        event = ShipmentTrackingEvent.create_from_shipment(
            shipment_id=self.id,
            event_type=ShipmentTrackingEventType.CANCELLED,
            status_before=self.status,
            status_after=ShipmentStatus.CANCELLED,
            description=reason or "Shipment cancelled",
        )
        self.status = ShipmentStatus.CANCELLED
        self.tracking_events.append(event)
        self.updated_at = datetime.utcnow()
        return event

    # ===== Query Methods =====

    def is_terminal(self) -> bool:
        """Check if shipment is in terminal status"""
        return self.status in (
            ShipmentStatus.DELIVERED,
            ShipmentStatus.RETURNED,
            ShipmentStatus.CANCELLED,
        )

    def is_active(self) -> bool:
        """Check if shipment is active"""
        return not self.is_terminal() and self.status != ShipmentStatus.FAILED_DELIVERY

    def can_transition_to(self, target_status: ShipmentStatus) -> bool:
        """Check if transition is valid"""
        valid_transitions = {
            ShipmentStatus.CREATED: [ShipmentStatus.PENDING_PICKUP, ShipmentStatus.CANCELLED],
            ShipmentStatus.PENDING_PICKUP: [ShipmentStatus.PICKED_UP, ShipmentStatus.CANCELLED],
            ShipmentStatus.PICKED_UP: [ShipmentStatus.IN_TRANSIT, ShipmentStatus.CANCELLED],
            ShipmentStatus.IN_TRANSIT: [ShipmentStatus.OUT_FOR_DELIVERY, ShipmentStatus.FAILED_DELIVERY],
            ShipmentStatus.OUT_FOR_DELIVERY: [ShipmentStatus.DELIVERED, ShipmentStatus.FAILED_DELIVERY],
            ShipmentStatus.FAILED_DELIVERY: [ShipmentStatus.RETURNED],
        }
        return target_status in valid_transitions.get(self.status, [])

    def get_latest_event(self) -> Optional[ShipmentTrackingEvent]:
        """Get latest tracking event"""
        return self.tracking_events[-1] if self.tracking_events else None

    def add_tracking_event(self, event: ShipmentTrackingEvent) -> None:
        """Add tracking event"""
        self.tracking_events.append(event)
        self.updated_at = datetime.utcnow()
