"""
Shipment Domain Repositories

Repository interfaces (contracts) for shipment domain.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from .entities import Shipment, ShipmentTrackingEvent, ShipmentStatus


class ShipmentRepository(ABC):
    """Repository interface for Shipment aggregate"""

    @abstractmethod
    def save(self, shipment: Shipment) -> Shipment:
        """Save or update shipment"""
        pass

    @abstractmethod
    def get_by_id(self, shipment_id: UUID) -> Optional[Shipment]:
        """Get shipment by ID"""
        pass

    @abstractmethod
    def get_by_reference(self, shipment_reference: str) -> Optional[Shipment]:
        """Get shipment by reference"""
        pass

    @abstractmethod
    def get_by_tracking_number(self, tracking_number: str) -> Optional[Shipment]:
        """Get shipment by tracking number"""
        pass

    @abstractmethod
    def get_by_order(self, order_id: UUID) -> Optional[Shipment]:
        """Get shipment by order ID (assumes one shipment per order)"""
        pass

    @abstractmethod
    def get_active_by_order(self, order_id: UUID) -> List[Shipment]:
        """Get active shipments for order"""
        pass

    @abstractmethod
    def get_by_carrier_shipment_id(self, carrier_shipment_id: str) -> Optional[Shipment]:
        """Get shipment by carrier reference"""
        pass

    @abstractmethod
    def list_by_status(self, status: ShipmentStatus, limit: int = 100) -> List[Shipment]:
        """List shipments by status"""
        pass

    @abstractmethod
    def list_by_order_ids(self, order_ids: List[UUID]) -> List[Shipment]:
        """List shipments for multiple orders"""
        pass


class ShipmentTrackingEventRepository(ABC):
    """Repository interface for tracking events"""

    @abstractmethod
    def save(self, event: ShipmentTrackingEvent) -> ShipmentTrackingEvent:
        """Save tracking event"""
        pass

    @abstractmethod
    def get_by_id(self, event_id: UUID) -> Optional[ShipmentTrackingEvent]:
        """Get event by ID"""
        pass

    @abstractmethod
    def get_by_shipment(self, shipment_id: UUID) -> List[ShipmentTrackingEvent]:
        """Get all events for a shipment"""
        pass

    @abstractmethod
    def get_by_provider_event_id(self, provider_event_id: str) -> Optional[ShipmentTrackingEvent]:
        """Get event by provider event ID"""
        pass
