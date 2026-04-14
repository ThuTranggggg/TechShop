"""
Shipment Application DTOs

Data transfer objects for request/response.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID


@dataclass
class ReceiverAddressDTO:
    """Receiver address DTO"""
    name: str
    phone: str
    address_line1: str
    address_line2: Optional[str] = None
    ward: Optional[str] = None
    district: str = ""
    city: str = ""
    country: str = "VN"
    postal_code: Optional[str] = None


@dataclass
class ShipmentItemDTO:
    """Shipment item DTO"""
    order_item_id: Optional[UUID]
    product_id: UUID
    variant_id: Optional[UUID]
    sku: Optional[str]
    quantity: int
    product_name_snapshot: str
    variant_name_snapshot: Optional[str] = None


@dataclass
class CreateShipmentRequestDTO:
    """Request DTO for creating shipment"""
    order_id: UUID
    order_number: str
    user_id: Optional[UUID]
    receiver_name: str
    receiver_phone: str
    address_line1: str
    district: str
    city: str
    address_line2: Optional[str] = None
    ward: Optional[str] = None
    country: str = "VN"
    postal_code: Optional[str] = None
    items: List[dict] = None
    service_level: str = "standard"
    shipping_fee_amount: Optional[Decimal] = None
    currency: str = "VND"
    provider: str = "mock"
    idempotency_key: Optional[str] = None

    def to_dict(self):
        return asdict(self)


@dataclass
class ShipmentTrackingEventDTO:
    """Tracking event DTO"""
    id: str
    event_type: str
    status_after: str
    description: Optional[str] = None
    location: Optional[str] = None
    event_time: Optional[str] = None
    created_at: Optional[str] = None

    def to_dict(self):
        return asdict(self)


@dataclass
class ShipmentDetailDTO:
    """Shipment detail response DTO"""
    id: str
    shipment_reference: str
    tracking_number: str
    order_id: str
    order_number: str
    user_id: Optional[str]
    provider: str
    service_level: str
    status: str
    tracking_url: Optional[str] = None
    label_url: Optional[str] = None
    package_count: int = 1
    package_weight: Optional[str] = None
    shipping_fee_amount: Optional[str] = None
    currency: str = "VND"
    failure_reason: Optional[str] = None
    carrier_shipment_id: Optional[str] = None
    expected_delivery_at: Optional[str] = None
    shipped_at: Optional[str] = None
    delivered_at: Optional[str] = None
    cancelled_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    receiver_name: str = ""
    receiver_phone: str = ""
    address_line1: str = ""
    district: str = ""
    city: str = ""
    country: str = ""
    items: List[ShipmentItemDTO] = None
    latest_event: Optional[ShipmentTrackingEventDTO] = None
    events_count: int = 0

    def to_dict(self):
        data = asdict(self)
        if self.items:
            data["items"] = [item.to_dict() for item in self.items]
        if self.latest_event:
            data["latest_event"] = self.latest_event.to_dict()
        return data


@dataclass
class ShipmentStatusDTO:
    """Quick shipment status response DTO"""
    shipment_reference: str
    tracking_number: str
    status: str
    provider: str
    order_id: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    expected_delivery_at: Optional[str] = None
    delivered_at: Optional[str] = None
    current_location: Optional[str] = None

    def to_dict(self):
        return asdict(self)


@dataclass
class ShipmentTrackingResponseDTO:
    """Public tracking response DTO"""
    shipment_reference: str
    tracking_number: str
    status: str
    provider: str
    tracking_url: Optional[str] = None
    expected_delivery_at: Optional[str] = None
    delivered_at: Optional[str] = None
    current_location: Optional[str] = None
    events: List[ShipmentTrackingEventDTO] = None
    receiver_city: Optional[str] = None

    def to_dict(self):
        data = asdict(self)
        if self.events:
            data["events"] = [e.to_dict() for e in self.events]
        return data


def shipment_to_detail_dto(shipment: "Shipment") -> ShipmentDetailDTO:  # noqa: F821
    """Convert domain Shipment to detail DTO"""
    from modules.shipping.domain import Shipment
    
    items_dto = [
        ShipmentItemDTO(
            order_item_id=item.order_item_id,
            product_id=item.product_id,
            variant_id=item.variant_id,
            sku=item.sku,
            quantity=item.quantity,
            product_name_snapshot=item.product_name_snapshot,
            variant_name_snapshot=item.variant_name_snapshot,
        )
        for item in shipment.items
    ]
    
    latest_event_dto = None
    if shipment.tracking_events:
        latest_event = shipment.tracking_events[-1]
        latest_event_dto = ShipmentTrackingEventDTO(
            id=str(latest_event.id),
            event_type=latest_event.event_type.value,
            status_after=latest_event.status_after.value,
            description=latest_event.description,
            location=latest_event.location,
            event_time=latest_event.event_time.isoformat() if latest_event.event_time else None,
            created_at=latest_event.created_at.isoformat() if latest_event.created_at else None,
        )
    
    return ShipmentDetailDTO(
        id=str(shipment.id),
        shipment_reference=shipment.shipment_reference,
        tracking_number=shipment.tracking_number,
        order_id=str(shipment.order_id),
        order_number=shipment.order_number,
        user_id=str(shipment.user_id) if shipment.user_id else None,
        provider=shipment.provider.value,
        service_level=shipment.service_level.value,
        status=shipment.status.value,
        tracking_url=shipment.tracking_url,
        label_url=shipment.label_url,
        package_count=shipment.package_count,
        package_weight=str(shipment.package_weight) if shipment.package_weight else None,
        shipping_fee_amount=str(shipment.shipping_fee.amount) if shipment.shipping_fee else None,
        currency=shipment.shipping_fee.currency if shipment.shipping_fee else "VND",
        failure_reason=shipment.failure_reason,
        carrier_shipment_id=shipment.carrier_shipment_id,
        expected_delivery_at=shipment.expected_delivery_at.isoformat() if shipment.expected_delivery_at else None,
        shipped_at=shipment.shipped_at.isoformat() if shipment.shipped_at else None,
        delivered_at=shipment.delivered_at.isoformat() if shipment.delivered_at else None,
        cancelled_at=shipment.cancelled_at.isoformat() if shipment.cancelled_at else None,
        created_at=shipment.created_at.isoformat() if shipment.created_at else None,
        updated_at=shipment.updated_at.isoformat() if shipment.updated_at else None,
        receiver_name=shipment.receiver_address.name,
        receiver_phone=shipment.receiver_address.phone,
        address_line1=shipment.receiver_address.address_line1,
        district=shipment.receiver_address.district,
        city=shipment.receiver_address.city,
        country=shipment.receiver_address.country,
        items=items_dto,
        latest_event=latest_event_dto,
        events_count=len(shipment.tracking_events),
    )


def shipment_to_status_dto(shipment: "Shipment") -> ShipmentStatusDTO:  # noqa: F821
    """Convert Shipment to quick status DTO"""
    return ShipmentStatusDTO(
        shipment_reference=shipment.shipment_reference,
        tracking_number=shipment.tracking_number,
        status=shipment.status.value,
        provider=shipment.provider.value,
        order_id=str(shipment.order_id),
        created_at=shipment.created_at.isoformat() if shipment.created_at else None,
        updated_at=shipment.updated_at.isoformat() if shipment.updated_at else None,
        expected_delivery_at=shipment.expected_delivery_at.isoformat() if shipment.expected_delivery_at else None,
        delivered_at=shipment.delivered_at.isoformat() if shipment.delivered_at else None,
        current_location=None,  # Could be populated from latest event
    )


def shipment_to_tracking_response_dto(shipment: "Shipment") -> ShipmentTrackingResponseDTO:  # noqa: F821
    """Convert Shipment to public tracking response DTO"""
    events_dto = [
        ShipmentTrackingEventDTO(
            id=str(event.id),
            event_type=event.event_type.value,
            status_after=event.status_after.value,
            description=event.description,
            location=event.location,
            event_time=event.event_time.isoformat() if event.event_time else None,
            created_at=event.created_at.isoformat() if event.created_at else None,
        )
        for event in shipment.tracking_events
    ]
    
    current_location = None
    if shipment.tracking_events:
        for event in reversed(shipment.tracking_events):
            if event.location:
                current_location = event.location
                break
    
    return ShipmentTrackingResponseDTO(
        shipment_reference=shipment.shipment_reference,
        tracking_number=shipment.tracking_number,
        status=shipment.status.value,
        provider=shipment.provider.value,
        tracking_url=shipment.tracking_url,
        expected_delivery_at=shipment.expected_delivery_at.isoformat() if shipment.expected_delivery_at else None,
        delivered_at=shipment.delivered_at.isoformat() if shipment.delivered_at else None,
        current_location=current_location,
        events=events_dto,
        receiver_city=shipment.receiver_address.city,
    )
