"""
Shipment Module URLs

REST API URL routing.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from modules.shipping.presentation.views import (
    InternalShipmentViewSet,
    OperationsShipmentViewSet,
    PublicShipmentViewSet,
    MockShipmentViewSet,
)

router = DefaultRouter()
router.register(r"internal/shipments", InternalShipmentViewSet, basename="internal-shipment")
router.register(r"shipments", PublicShipmentViewSet, basename="public-shipment")
router.register(r"operations/shipments", OperationsShipmentViewSet, basename="operations-shipment")
router.register(r"mock-shipments", MockShipmentViewSet, basename="mock-shipment")

urlpatterns = [
    path("", include(router.urls)),
]
