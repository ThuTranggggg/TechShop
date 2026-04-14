"""
Shipment Repository Implementations

Persistence implementations using Django ORM.
"""

from typing import List, Optional
from uuid import UUID

from django.db import transaction

from modules.shipping.domain import (
    Shipment,
    ShipmentRepository,
    ShipmentStatus,
    ShipmentTrackingEvent,
    ShipmentTrackingEventRepository,
)
from .models import ShipmentModel, ShipmentItemModel, ShipmentTrackingEventModel


class ShipmentRepositoryImpl(ShipmentRepository):
    """Repository implementation for Shipment"""

    @transaction.atomic
    def save(self, shipment: Shipment) -> Shipment:
        """Save or update shipment"""
        # Save shipment model
        model = ShipmentModel.from_domain(shipment)
        model.save()
        
        # Save items
        shipment.items_to_delete = []  # Track deleted items
        existing_items = set(
            ShipmentItemModel.objects.filter(shipment_id=model.id).values_list(
                "id", flat=True
            )
        )
        
        for item in shipment.items:
            ShipmentItemModel.from_domain(model.id, item).save()
        
        # Save tracking events
        for event in shipment.tracking_events:
            event_model = ShipmentTrackingEventModel.from_domain(event)
            if not ShipmentTrackingEventModel.objects.filter(id=event.id).exists():
                event_model.save()
        
        # Reload and return
        return self.get_by_id(model.id)

    def get_by_id(self, shipment_id: UUID) -> Optional[Shipment]:
        """Get shipment by ID"""
        try:
            model = ShipmentModel.objects.get(id=shipment_id)
            return model.to_domain()
        except ShipmentModel.DoesNotExist:
            return None

    def get_by_reference(self, shipment_reference: str) -> Optional[Shipment]:
        """Get shipment by reference"""
        try:
            model = ShipmentModel.objects.get(shipment_reference=shipment_reference)
            return model.to_domain()
        except ShipmentModel.DoesNotExist:
            return None

    def get_by_tracking_number(self, tracking_number: str) -> Optional[Shipment]:
        """Get shipment by tracking number"""
        try:
            model = ShipmentModel.objects.get(tracking_number=tracking_number)
            return model.to_domain()
        except ShipmentModel.DoesNotExist:
            return None

    def get_by_order(self, order_id: UUID) -> Optional[Shipment]:
        """Get shipment by order ID"""
        try:
            model = ShipmentModel.objects.filter(order_id=order_id).latest("created_at")
            return model.to_domain()
        except ShipmentModel.DoesNotExist:
            return None

    def get_active_by_order(self, order_id: UUID) -> List[Shipment]:
        """Get active shipments for order"""
        active_statuses = [
            ShipmentStatus.CREATED,
            ShipmentStatus.PENDING_PICKUP,
            ShipmentStatus.PICKED_UP,
            ShipmentStatus.IN_TRANSIT,
            ShipmentStatus.OUT_FOR_DELIVERY,
        ]
        models = ShipmentModel.objects.filter(
            order_id=order_id,
            status__in=[s.value for s in active_statuses],
        )
        return [m.to_domain() for m in models]

    def get_by_carrier_shipment_id(self, carrier_shipment_id: str) -> Optional[Shipment]:
        """Get shipment by carrier reference"""
        try:
            model = ShipmentModel.objects.get(
                carrier_shipment_id=carrier_shipment_id
            )
            return model.to_domain()
        except ShipmentModel.DoesNotExist:
            return None

    def list_by_status(self, status: ShipmentStatus, limit: int = 100) -> List[Shipment]:
        """List shipments by status"""
        models = ShipmentModel.objects.filter(status=status.value)[:limit]
        return [m.to_domain() for m in models]

    def list_by_order_ids(self, order_ids: List[UUID]) -> List[Shipment]:
        """List shipments for multiple orders"""
        models = ShipmentModel.objects.filter(order_id__in=order_ids)
        return [m.to_domain() for m in models]


class ShipmentTrackingEventRepositoryImpl(ShipmentTrackingEventRepository):
    """Repository implementation for tracking events"""

    def save(self, event: ShipmentTrackingEvent) -> ShipmentTrackingEvent:
        """Save tracking event"""
        model = ShipmentTrackingEventModel.from_domain(event)
        model.save()
        return model.to_domain()

    def get_by_id(self, event_id: UUID) -> Optional[ShipmentTrackingEvent]:
        """Get event by ID"""
        try:
            model = ShipmentTrackingEventModel.objects.get(id=event_id)
            return model.to_domain()
        except ShipmentTrackingEventModel.DoesNotExist:
            return None

    def get_by_shipment(self, shipment_id: UUID) -> List[ShipmentTrackingEvent]:
        """Get all events for a shipment"""
        models = ShipmentTrackingEventModel.objects.filter(
            shipment_id=shipment_id
        ).order_by("created_at")
        return [m.to_domain() for m in models]

    def get_by_provider_event_id(self, provider_event_id: str) -> Optional[ShipmentTrackingEvent]:
        """Get event by provider event ID"""
        try:
            model = ShipmentTrackingEventModel.objects.get(
                provider_event_id=provider_event_id
            )
            return model.to_domain()
        except ShipmentTrackingEventModel.DoesNotExist:
            return None
