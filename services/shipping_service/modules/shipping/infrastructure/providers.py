"""
Shipping Provider Abstraction

Base interface and implementations for shipping providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
import uuid
import secrets

from modules.shipping.domain import (
    Shipment,
    ShipmentStatus,
    ShippingProvider,
)


@dataclass
class CreateShipmentResponse:
    """Response from provider create_shipment"""
    success: bool
    message: str
    carrier_shipment_id: Optional[str] = None
    tracking_number: Optional[str] = None
    tracking_url: Optional[str] = None
    label_url: Optional[str] = None
    expected_delivery_at: Optional[datetime] = None
    raw_response: Optional[dict] = None


@dataclass
class ShipmentStatusResponse:
    """Response from provider get_status"""
    success: bool
    status: Optional[ShipmentStatus] = None
    location: Optional[str] = None
    description: Optional[str] = None
    raw_response: Optional[dict] = None


@dataclass
class CallbackPayload:
    """Parsed callback payload"""
    provider: str
    provider_event_id: str
    carrier_shipment_id: str
    shipment_reference: str
    status: ShipmentStatus
    location: Optional[str] = None
    message: Optional[str] = None
    raw_payload: Optional[dict] = None


class BaseShippingProvider(ABC):
    """Base class for shipping providers"""

    @abstractmethod
    def create_shipment(self, shipment: Shipment) -> CreateShipmentResponse:
        """Create shipment at carrier"""
        pass

    @abstractmethod
    def get_status(self, shipment: Shipment) -> ShipmentStatusResponse:
        """Get shipment status from carrier"""
        pass

    @abstractmethod
    def cancel_shipment(self, shipment: Shipment) -> bool:
        """Cancel shipment at carrier"""
        pass

    @abstractmethod
    def parse_callback(self, payload: dict) -> CallbackPayload:
        """Parse provider callback"""
        pass


class MockShippingProvider(BaseShippingProvider):
    """Mock shipping provider for development/testing"""

    def __init__(self):
        self.shipments = {}  # In-memory store for testing

    def create_shipment(self, shipment: Shipment) -> CreateShipmentResponse:
        """Create mock shipment"""
        try:
            carrier_shipment_id = f"MOCK-{uuid.uuid4().hex[:8].upper()}"
            tracking_url = f"http://localhost:8006/api/v1/shipments/{shipment.shipment_reference}/tracking/"
            expected_delivery = datetime.utcnow() + timedelta(days=3)
            
            # Store for mock progression
            self.shipments[shipment.shipment_reference] = {
                "carrier_shipment_id": carrier_shipment_id,
                "status": ShipmentStatus.PENDING_PICKUP,
                "created_at": datetime.utcnow(),
                "events": [],
            }
            
            return CreateShipmentResponse(
                success=True,
                message="Mock shipment created successfully",
                carrier_shipment_id=carrier_shipment_id,
                tracking_number=shipment.tracking_number,
                tracking_url=tracking_url,
                expected_delivery_at=expected_delivery,
                raw_response={
                    "carrier_shipment_id": carrier_shipment_id,
                    "status": "pending_pickup",
                },
            )
        except Exception as e:
            return CreateShipmentResponse(
                success=False,
                message=f"Failed to create mock shipment: {str(e)}",
            )

    def get_status(self, shipment: Shipment) -> ShipmentStatusResponse:
        """Get mock shipment status"""
        try:
            if shipment.carrier_shipment_id not in self.shipments:
                return ShipmentStatusResponse(
                    success=False,
                    status=None,
                )
            
            mock_data = self.shipments[shipment.carrier_shipment_id]
            status = mock_data.get("status", ShipmentStatus.PENDING_PICKUP)
            
            return ShipmentStatusResponse(
                success=True,
                status=status,
                location="Mock Processing Center",
                raw_response={"status": status.value},
            )
        except Exception as e:
            return ShipmentStatusResponse(success=False)

    def cancel_shipment(self, shipment: Shipment) -> bool:
        """Cancel mock shipment"""
        try:
            if shipment.carrier_shipment_id in self.shipments:
                self.shipments[shipment.carrier_shipment_id]["status"] = ShipmentStatus.CANCELLED
            return True
        except:
            return False

    def parse_callback(self, payload: dict) -> CallbackPayload:
        """Parse mock callback"""
        return CallbackPayload(
            provider=ShippingProvider.MOCK.value,
            provider_event_id=payload.get("provider_event_id", f"MOCK-{uuid.uuid4().hex[:8]}"),
            carrier_shipment_id=payload.get("carrier_shipment_id", ""),
            shipment_reference=payload.get("shipment_reference", ""),
            status=ShipmentStatus(payload.get("status", "in_transit")),
            location=payload.get("location", "Mock Location"),
            message=payload.get("message", "Mock update"),
            raw_payload=payload,
        )

    def advance_status(
        self,
        shipment: Shipment,
        target_status: ShipmentStatus,
    ) -> ShipmentStatusResponse:
        """
        Advance mock shipment status.
        
        Useful for local development/testing.
        """
        try:
            key = shipment.carrier_shipment_id or shipment.shipment_reference
            if key not in self.shipments:
                return ShipmentStatusResponse(success=False)
            
            self.shipments[key]["status"] = target_status
            self.shipments[key]["events"].append({
                "status": target_status.value,
                "timestamp": datetime.utcnow().isoformat(),
            })
            
            return ShipmentStatusResponse(
                success=True,
                status=target_status,
                raw_response={"status": target_status.value},
            )
        except Exception as e:
            return ShipmentStatusResponse(success=False)


class ShippingProviderFactory:
    """Factory for creating provider instances"""

    _providers = {
        ShippingProvider.MOCK.value: MockShippingProvider,
        # Future providers:
        # ShippingProvider.GHN.value: GHNProvider,
        # ShippingProvider.GHTK.value: GHTKProvider,
    }

    @classmethod
    def get_provider(cls, provider_name: str) -> BaseShippingProvider:
        """Get provider instance"""
        provider_class = cls._providers.get(provider_name)
        if not provider_class:
            raise ValueError(f"Unknown provider: {provider_name}")
        return provider_class()

    @classmethod
    def register_provider(cls, name: str, provider_class: type) -> None:
        """Register a new provider"""
        cls._providers[name] = provider_class
