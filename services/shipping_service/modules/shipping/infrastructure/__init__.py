"""
Infrastructure Layer

Persistence, providers, external integrations.
"""

from .models import ShipmentModel, ShipmentItemModel, ShipmentTrackingEventModel
from .repositories import ShipmentRepositoryImpl, ShipmentTrackingEventRepositoryImpl
from .providers import BaseShippingProvider, MockShippingProvider, ShippingProviderFactory
from .clients import OrderServiceClient

__all__ = [
    "ShipmentModel",
    "ShipmentItemModel",
    "ShipmentTrackingEventModel",
    "ShipmentRepositoryImpl",
    "ShipmentTrackingEventRepositoryImpl",
    "BaseShippingProvider",
    "MockShippingProvider",
    "ShippingProviderFactory",
    "OrderServiceClient",
]
