"""
URL routing for Cart service module.
"""
from django.urls import path
from rest_framework.routers import SimpleRouter

from .presentation.api import CustomerCartViewSet, InternalCartViewSet

router = SimpleRouter()

# Customer-facing cart endpoints
router.register(r'cart', CustomerCartViewSet, basename='cart')

# Internal cart endpoints
router.register(r'internal/carts', InternalCartViewSet, basename='internal-carts')

urlpatterns = router.urls
