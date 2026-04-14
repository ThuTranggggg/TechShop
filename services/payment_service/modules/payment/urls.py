"""
Payment Module URLs

Register payment API endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .presentation.views import (
    PaymentViewSet,
    PaymentWebhookViewSet,
)

router = DefaultRouter()
router.register(r"payments", PaymentViewSet, basename="payment")
router.register(r"webhooks", PaymentWebhookViewSet, basename="webhook")

urlpatterns = [
    path("", include(router.urls)),
]
