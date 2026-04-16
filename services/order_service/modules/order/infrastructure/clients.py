"""
Infrastructure clients for inter-service communication.

Clients for cart_service, inventory_service, payment_service, shipping_service, ai_service.
"""

import os
import httpx
import logging
from typing import Optional, Dict, List, Any
from uuid import UUID
from decimal import Decimal
from datetime import datetime

logger = logging.getLogger(__name__)


class CartServiceClient:
    """
    Client for communicating with cart_service.
    """
    
    def __init__(self, base_url: str = None, timeout: float = 5.0, internal_key: str = None):
        self.base_url = base_url or os.getenv("CART_SERVICE_URL", "http://cart_service:8003")
        self.timeout = timeout
        self.internal_key = internal_key or os.getenv("INTERNAL_SERVICE_KEY", "")
    
    def validate_cart(self, cart_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """Validate cart exists and belongs to user."""
        url = f"{self.base_url}/api/v1/internal/carts/{cart_id}/validate/"
        headers = {
            "X-Internal-Service-Key": self.internal_key,
            "X-User-ID": str(user_id),
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, headers=headers)
                resp.raise_for_status()
                return resp.json().get("data", {})
        except httpx.HTTPError as e:
            logger.error(f"Failed to validate cart {cart_id}: {e}")
            raise ValueError(f"Cart validation failed: {str(e)}")
    
    def build_checkout_payload(self, cart_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """Build checkout payload from cart."""
        url = f"{self.base_url}/api/v1/internal/carts/{cart_id}/checkout-payload/"
        headers = {
            "X-Internal-Service-Key": self.internal_key,
            "X-User-ID": str(user_id),
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, headers=headers)
                resp.raise_for_status()
                return resp.json().get("data", {})
        except httpx.HTTPError as e:
            logger.error(f"Failed to build checkout payload for cart {cart_id}: {e}")
            raise ValueError(f"Checkout payload failed: {str(e)}")
    
    def mark_cart_checked_out(self, cart_id: UUID) -> Dict[str, Any]:
        """Mark cart as checked out after order creation."""
        url = f"{self.base_url}/api/v1/internal/carts/{cart_id}/mark-checked-out/"
        headers = {
            "X-Internal-Service-Key": self.internal_key,
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, headers=headers)
                resp.raise_for_status()
                return resp.json().get("data", {})
        except httpx.HTTPError as e:
            logger.warning(f"Failed to mark cart {cart_id} checked out: {e}")
            return {}


class ProductServiceClient:
    """Client for retrieving product snapshots for order item history."""

    def __init__(self, base_url: str = None, timeout: float = 5.0):
        self.base_url = base_url or os.getenv("PRODUCT_SERVICE_URL", "http://gateway/product")
        self.timeout = timeout

    def get_product_detail(self, product_id: UUID) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/catalog/products/{product_id}/"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url)
                resp.raise_for_status()
                payload = resp.json()
                return payload.get("data", payload)
        except httpx.HTTPError as e:
            logger.warning(f"Failed to fetch product {product_id}: {e}")
            return {}


class InventoryServiceClient:
    """
    Client for communicating with inventory_service.
    """
    
    def __init__(self, base_url: str = None, timeout: float = 5.0, internal_key: str = None):
        self.base_url = base_url or os.getenv("INVENTORY_SERVICE_URL", "http://inventory_service:8007")
        self.timeout = timeout
        self.internal_key = internal_key or os.getenv("INTERNAL_SERVICE_KEY", "")
    
    def create_reservations(
        self,
        items: List[Dict[str, Any]],
        order_id: UUID,
        user_id: UUID,
    ) -> Dict[str, Any]:
        """
        Reserve stock for order items.
        
        Items format:
        [
            {
                "product_id": "...",
                "variant_id": "...", (optional)
                "quantity": 5,
            },
            ...
        ]
        
        Returns reservation refs.
        """
        url = f"{self.base_url}/api/v1/internal/inventory/reserve/"
        payload = {
            "order_id": str(order_id),
            "user_id": str(user_id),
            "items": items,
        }
        headers = {
            "X-Internal-Service": "order_service",
            "X-Internal-Token": self.internal_key,
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                return resp.json().get("data", {})
        except httpx.HTTPError as e:
            logger.error(f"Failed to create reservations for order {order_id}: {e}")
            raise ValueError(f"Stock reservation failed: {str(e)}")
    
    def confirm_reservations(
        self,
        reservation_ids: List[str],
        order_id: UUID,
    ) -> Dict[str, Any]:
        """Confirm stock reservations after payment success."""
        url = f"{self.base_url}/api/v1/internal/inventory/confirm/"
        payload = {
            "order_id": str(order_id),
            "reservation_ids": reservation_ids,
        }
        headers = {
            "X-Internal-Service": "order_service",
            "X-Internal-Token": self.internal_key,
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                return resp.json().get("data", {})
        except httpx.HTTPError as e:
            logger.error(f"Failed to confirm reservations for order {order_id}: {e}")
            raise ValueError(f"Reservation confirmation failed: {str(e)}")
    
    def release_reservations(
        self,
        reservation_ids: List[str],
        order_id: UUID,
        reason: str = "Order cancelled",
    ) -> Dict[str, Any]:
        """Release stock reservations (on payment failure, order cancel, etc)."""
        url = f"{self.base_url}/api/v1/internal/inventory/release/"
        payload = {
            "order_id": str(order_id),
            "reservation_ids": reservation_ids,
            "reason": reason,
        }
        headers = {
            "X-Internal-Service": "order_service",
            "X-Internal-Token": self.internal_key,
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                return resp.json().get("data", {})
        except httpx.HTTPError as e:
            logger.error(f"Failed to release reservations for order {order_id}: {e}")
            raise ValueError(f"Reservation release failed: {str(e)}")


class PaymentServiceClient:
    """
    Client for communicating with payment_service.
    """
    
    def __init__(self, base_url: str = None, timeout: float = 5.0, internal_key: str = None):
        self.base_url = base_url or os.getenv("PAYMENT_SERVICE_URL", "http://payment_service:8005")
        self.timeout = timeout
        self.internal_key = internal_key or os.getenv("INTERNAL_SERVICE_KEY", "")
    
    def create_payment(
        self,
        order_id: UUID,
        user_id: UUID,
        amount: Decimal,
        currency: str,
        order_number: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create payment request.
        
        Returns payment info with payment_id and payment_reference.
        """
        url = f"{self.base_url}/api/v1/internal/payments/create/"
        payload = {
            "order_id": str(order_id),
            "user_id": str(user_id),
            "amount": str(amount),
            "currency": currency,
            "order_number": order_number,
            "metadata": metadata or {},
        }
        headers = {
            "X-Internal-Service-Key": self.internal_key,
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                return resp.json().get("data", {})
        except httpx.HTTPError as e:
            logger.error(f"Failed to create payment for order {order_id}: {e}")
            raise ValueError(f"Payment creation failed: {str(e)}")
    
    def get_payment_status(self, payment_id: UUID) -> Dict[str, Any]:
        """Get current payment status."""
        url = f"{self.base_url}/api/v1/internal/payments/{payment_id}/"
        headers = {
            "X-Internal-Service-Key": self.internal_key,
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url, headers=headers)
                resp.raise_for_status()
                return resp.json().get("data", {})
        except httpx.HTTPError as e:
            logger.error(f"Failed to get payment status {payment_id}: {e}")
            raise ValueError(f"Payment status fetch failed: {str(e)}")
    
    def refund_payment(
        self,
        payment_id: UUID,
        reason: str = "Inventory confirmation failed",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Initiate refund for a payment (compensating transaction).
        
        Used when inventory confirmation fails after payment success.
        This is a critical error recovery mechanism.
        """
        url = f"{self.base_url}/api/v1/internal/payments/{payment_id}/refund/"
        payload = {
            "reason": reason,
            "metadata": metadata or {},
        }
        headers = {
            "X-Internal-Service-Key": self.internal_key,
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                return resp.json().get("data", {})
        except httpx.HTTPError as e:
            logger.error(f"Failed to refund payment {payment_id}: {e}")
            raise ValueError(f"Payment refund failed: {str(e)}")


class ShippingServiceClient:
    """
    Client for communicating with shipping_service.
    """
    
    def __init__(self, base_url: str = None, timeout: float = 5.0, internal_key: str = None):
        self.base_url = base_url or os.getenv("SHIPPING_SERVICE_URL", "http://shipping_service:8008")
        self.timeout = timeout
        self.internal_key = internal_key or os.getenv("INTERNAL_SERVICE_KEY", "")
    
    def create_shipment(
        self,
        order_id: UUID,
        order_number: str,
        items: List[Dict[str, Any]],
        shipping_address: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create shipment request.
        
        Returns shipment info with shipment_id and shipment_reference.
        """
        url = f"{self.base_url}/api/v1/internal/shipments/create/"
        payload = {
            "order_id": str(order_id),
            "order_number": order_number,
            "items": items,
            "shipping_address": shipping_address,
            "metadata": metadata or {},
        }
        headers = {
            "X-Internal-Service-Key": self.internal_key,
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                return resp.json().get("data", {})
        except httpx.HTTPError as e:
            logger.error(f"Failed to create shipment for order {order_id}: {e}")
            raise ValueError(f"Shipment creation failed: {str(e)}")
    
    def get_shipment_status(self, shipment_id: UUID) -> Dict[str, Any]:
        """Get shipment status."""
        url = f"{self.base_url}/api/v1/internal/shipments/{shipment_id}/"
        headers = {
            "X-Internal-Service-Key": self.internal_key,
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url, headers=headers)
                resp.raise_for_status()
                return resp.json().get("data", {})
        except httpx.HTTPError as e:
            logger.error(f"Failed to get shipment status {shipment_id}: {e}")
            raise ValueError(f"Shipment status fetch failed: {str(e)}")


class AIServiceClient:
    """
    Client for communicating with ai_service.
    
    Non-blocking client for emitting order events to AI service.
    Failures are logged but do not fail the order creation.
    """
    
    def __init__(self, base_url: str = None, timeout: float = 3.0, internal_key: str = None):
        self.base_url = base_url or os.getenv("AI_SERVICE_URL", "http://ai_service:8000")
        self.timeout = timeout
        self.internal_key = internal_key or os.getenv("INTERNAL_SERVICE_KEY", "")
    
    def emit_order_event(
        self,
        event_type: str,
        user_id: UUID,
        order_id: UUID,
        order_number: str,
        total_items: int,
        order_value: Decimal,
        products: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Emit order event to AI service for behavioral tracking.
        
        Event types: order_created, payment_success, order_shipped, order_delivered
        
        Returns True if successful, False if failed (non-blocking).
        This is a fire-and-forget operation - failures are logged but don't fail the order.
        """
        url = f"{self.base_url}/api/v1/internal/ai/events/"
        payload = {
            "event_type": event_type,
            "user_id": str(user_id),
            "order_id": str(order_id),
            "order_number": order_number,
            "total_items": total_items,
            "order_value": str(order_value),
            "products": products,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }
        headers = {
            "X-Internal-Service-Key": self.internal_key,
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                logger.info(f"Order event '{event_type}' emitted to AI service for order {order_id}")
                return True
        except httpx.HTTPError as e:
            logger.warning(f"Failed to emit order event to AI service: {e} (non-blocking)")
            return False
        except Exception as e:
            logger.warning(f"Unexpected error emitting order event to AI service: {e} (non-blocking)")
            return False


class UserServiceClient:
    """
    Client for communicating with user_service.
    
    Used for user address validation and profile information.
    """
    
    def __init__(self, base_url: str = None, timeout: float = 5.0, internal_key: str = None):
        self.base_url = base_url or os.getenv("USER_SERVICE_URL", "http://user_service:8001")
        self.timeout = timeout
        self.internal_key = internal_key or os.getenv("INTERNAL_SERVICE_KEY", "")
    
    def validate_user_address(
        self,
        user_id: UUID,
        shipping_address: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate shipping address against user's known addresses.
        
        Returns:
        {
            "is_valid": bool,
            "is_registered_address": bool,
            "address_id": UUID or None,
            "message": str
        }
        
        Non-blocking: If validation fails, logs warning and returns {"is_valid": False}.
        """
        url = f"{self.base_url}/api/v1/internal/users/{user_id}/validate-address/"
        payload = {"address": shipping_address}
        headers = {
            "X-Internal-Service-Key": self.internal_key,
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                return resp.json().get("data", {"is_valid": False})
        except httpx.HTTPError as e:
            logger.warning(f"Failed to validate address for user {user_id}: {e}")
            return {"is_valid": False, "message": str(e)}
        except Exception as e:
            logger.warning(f"Unexpected error validating user address: {e}")
            return {"is_valid": False, "message": str(e)}

    def get_user_by_id(self, user_id: UUID) -> Dict[str, Any]:
        """
        Fetch the user's public profile for order snapshots.

        Order creation needs a stable customer snapshot even when the cart
        payload does not include customer metadata.
        """
        url = f"{self.base_url}/api/v1/internal/users/get/"
        headers = {
            "X-Internal-Service-Key": self.internal_key,
            "Content-Type": "application/json",
        }
        params = {"user_id": str(user_id)}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url, params=params, headers=headers)
                resp.raise_for_status()
                return resp.json().get("data", {})
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch user {user_id}: {e}")
            raise ValueError(f"User lookup failed: {str(e)}")
