"""
URL routing for Inventory module.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .presentation.api import AdminStockItemViewSet, InternalInventoryViewSet

router = DefaultRouter()
router.register(r"admin/inventory/stock-items", AdminStockItemViewSet, basename="admin-stock-items")
router.register(r"internal/inventory", InternalInventoryViewSet, basename="internal-inventory")

urlpatterns = [
    path("", include(router.urls)),
]
