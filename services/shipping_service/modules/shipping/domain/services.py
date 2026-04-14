"""
Shipment Domain Services

Business logic services at domain layer.
"""

from typing import Optional, Tuple
from uuid import UUID

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


class ShipmentValidator:
    """Validates shipment business rules"""

    @staticmethod
    def validate_receiver_address(address: ReceiverAddress) -> Tuple[bool, Optional[str]]:
        """Validate receiver address"""
        if not address.is_valid():
            return False, "Invalid receiver address: all required fields must be filled"
        if len(address.phone) < 7:
            return False, "Phone number must be at least 7 digits"
        if len(address.name) < 2:
            return False, "Receiver name must be at least 2 characters"
        return True, None

    @staticmethod
    def validate_shipment_items(items: list) -> Tuple[bool, Optional[str]]:
        """Validate shipment items"""
        if not items:
            return False, "Shipment must have at least one item"
        
        for item in items:
            if not item.is_valid():
                return False, f"Invalid item: {item.product_name_snapshot}"
        
        return True, None

    @staticmethod
    def validate_shipment_creation(
        order_id: UUID,
        receiver_address: ReceiverAddress,
        items: list,
        provider: ShippingProvider,
        service_level: ShippingServiceLevel,
    ) -> Tuple[bool, Optional[str]]:
        """Validate shipment creation payload"""
        if not order_id:
            return False, "order_id is required"
        
        is_valid, error = ShipmentValidator.validate_receiver_address(receiver_address)
        if not is_valid:
            return False, error
        
        is_valid, error = ShipmentValidator.validate_shipment_items(items)
        if not is_valid:
            return False, error
        
        if not isinstance(provider, ShippingProvider):
            return False, "Invalid provider"
        
        if not isinstance(service_level, ShippingServiceLevel):
            return False, "Invalid service level"
        
        return True, None

    @staticmethod
    def validate_transition(
        current_status: ShipmentStatus,
        target_status: ShipmentStatus,
    ) -> Tuple[bool, Optional[str]]:
        """Validate status transition"""
        valid_transitions = {
            ShipmentStatus.CREATED: [ShipmentStatus.PENDING_PICKUP, ShipmentStatus.CANCELLED],
            ShipmentStatus.PENDING_PICKUP: [ShipmentStatus.PICKED_UP, ShipmentStatus.CANCELLED],
            ShipmentStatus.PICKED_UP: [ShipmentStatus.IN_TRANSIT, ShipmentStatus.CANCELLED],
            ShipmentStatus.IN_TRANSIT: [ShipmentStatus.OUT_FOR_DELIVERY, ShipmentStatus.FAILED_DELIVERY],
            ShipmentStatus.OUT_FOR_DELIVERY: [ShipmentStatus.DELIVERED, ShipmentStatus.FAILED_DELIVERY],
            ShipmentStatus.FAILED_DELIVERY: [ShipmentStatus.RETURNED],
            ShipmentStatus.RETURNED: [],
            ShipmentStatus.CANCELLED: [],
            ShipmentStatus.DELIVERED: [],
        }
        
        allowed = valid_transitions.get(current_status, [])
        if target_status not in allowed:
            return False, f"Cannot transition from {current_status.value} to {target_status.value}"
        
        return True, None


class ShipmentFactory:
    """Factory for creating shipment entities"""

    @staticmethod
    def create_shipment(
        order_id: UUID,
        order_number: str,
        user_id: Optional[UUID],
        shipment_reference: str,
        tracking_number: str,
        receiver_address: ReceiverAddress,
        items: list,
        provider: ShippingProvider,
        service_level: ShippingServiceLevel,
        tracking_url: Optional[str] = None,
        shipping_fee: Optional[Money] = None,
        expected_delivery_at: Optional[object] = None,
        metadata: Optional[dict] = None,
    ) -> Shipment:
        """
        Factory method to create a new shipment.
        
        Validates input and creates shipment aggregate.
        """
        from uuid import uuid4

        # Validate
        is_valid, error = ShipmentValidator.validate_shipment_creation(
            order_id=order_id,
            receiver_address=receiver_address,
            items=items,
            provider=provider,
            service_level=service_level,
        )
        if not is_valid:
            raise ValueError(error)

        # Create shipment
        shipment = Shipment(
            id=uuid4(),
            order_id=order_id,
            order_number=order_number,
            user_id=user_id,
            shipment_reference=shipment_reference,
            tracking_number=tracking_number,
            receiver_address=receiver_address,
            items=items,
            provider=provider,
            service_level=service_level,
            status=ShipmentStatus.CREATED,
            tracking_url=tracking_url,
            shipping_fee=shipping_fee,
            expected_delivery_at=expected_delivery_at,
            metadata=metadata or {},
        )

        # Create initial tracking event
        initial_event = ShipmentTrackingEvent.create_from_shipment(
            shipment_id=shipment.id,
            event_type=ShipmentTrackingEventType.SHIPMENT_CREATED,
            status_before=None,
            status_after=ShipmentStatus.CREATED,
            description=f"Shipment created with tracking #{tracking_number}",
        )
        shipment.tracking_events.append(initial_event)

        return shipment


class ShipmentStateService:
    """Domain service for shipment state transitions"""

    @staticmethod
    def transition_to_pending_pickup(shipment: Shipment) -> None:
        """Transition shipment to pending pickup"""
        is_valid, error = ShipmentValidator.validate_transition(
            shipment.status,
            ShipmentStatus.PENDING_PICKUP,
        )
        if not is_valid:
            raise ValueError(error)
        
        shipment.transition_to_pending_pickup()

    @staticmethod
    def mark_picked_up(shipment: Shipment) -> None:
        """Mark shipment as picked up"""
        is_valid, error = ShipmentValidator.validate_transition(
            shipment.status,
            ShipmentStatus.PICKED_UP,
        )
        if not is_valid:
            raise ValueError(error)
        
        shipment.mark_picked_up()

    @staticmethod
    def mark_in_transit(shipment: Shipment, location: Optional[str] = None) -> None:
        """Mark shipment as in transit"""
        is_valid, error = ShipmentValidator.validate_transition(
            shipment.status,
            ShipmentStatus.IN_TRANSIT,
        )
        if not is_valid:
            raise ValueError(error)
        
        shipment.mark_in_transit(location=location)

    @staticmethod
    def mark_out_for_delivery(shipment: Shipment, location: Optional[str] = None) -> None:
        """Mark shipment as out for delivery"""
        is_valid, error = ShipmentValidator.validate_transition(
            shipment.status,
            ShipmentStatus.OUT_FOR_DELIVERY,
        )
        if not is_valid:
            raise ValueError(error)
        
        shipment.mark_out_for_delivery(location=location)

    @staticmethod
    def mark_delivered(shipment: Shipment, location: Optional[str] = None) -> None:
        """Mark shipment as delivered"""
        is_valid, error = ShipmentValidator.validate_transition(
            shipment.status,
            ShipmentStatus.DELIVERED,
        )
        if not is_valid:
            raise ValueError(error)
        
        shipment.mark_delivered(location=location)

    @staticmethod
    def mark_failed_delivery(
        shipment: Shipment,
        reason: str,
        location: Optional[str] = None,
    ) -> None:
        """Mark shipment delivery as failed"""
        is_valid, error = ShipmentValidator.validate_transition(
            shipment.status,
            ShipmentStatus.FAILED_DELIVERY,
        )
        if not is_valid:
            raise ValueError(error)
        
        shipment.mark_failed_delivery(reason=reason, location=location)

    @staticmethod
    def mark_returned(shipment: Shipment, location: Optional[str] = None) -> None:
        """Mark shipment as returned"""
        is_valid, error = ShipmentValidator.validate_transition(
            shipment.status,
            ShipmentStatus.RETURNED,
        )
        if not is_valid:
            raise ValueError(error)
        
        shipment.mark_returned(location=location)

    @staticmethod
    def cancel(shipment: Shipment, reason: Optional[str] = None) -> None:
        """Cancel shipment"""
        shipment.cancel(reason=reason)
