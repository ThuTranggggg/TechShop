"""
Inter-service clients for Cart infrastructure.

These clients communicate with other microservices.
"""
import os
import logging
from typing import Optional, Dict, List, Any
from abc import ABC, abstractmethod
import httpx
from decimal import Decimal
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def _normalize_internal_url(raw_url: str, fallback_url: str) -> str:
    """Map localhost/127.0.0.1 URLs to docker-internal service URLs."""
    try:
        parsed = urlparse(raw_url)
        host = parsed.hostname or ""
        if host in {"localhost", "127.0.0.1"}:
            return fallback_url
        return raw_url
    except Exception:
        return fallback_url


class ProductServiceClient(ABC):
    """
    Client for communicating with product_service.
    """
    
    @abstractmethod
    def get_product_snapshot(
        self,
        product_id: str,
        variant_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get product snapshot for cart display."""
        pass
    
    @abstractmethod
    def validate_product_active(
        self,
        product_id: str,
        variant_id: Optional[str] = None
    ) -> bool:
        """Check if product is active and published."""
        pass
    
    @abstractmethod
    def bulk_get_product_snapshots(
        self,
        items: List[Dict[str, str]]
    ) -> Dict[str, Dict[str, Any]]:
        """Bulk fetch snapshots for multiple products."""
        pass


class InventoryServiceClient(ABC):
    """
    Client for communicating with inventory_service.
    """
    
    @abstractmethod
    def check_availability(
        self,
        items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Check availability for multiple items."""
        pass
    
    @abstractmethod
    def get_product_availability(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get availability info for a product."""
        pass


class HttpProductServiceClient(ProductServiceClient):
    """
    HTTP client for product_service.
    """
    
    def __init__(self):
        raw_base_url = os.getenv("PRODUCT_SERVICE_URL", "http://product_service:8002")
        self.base_url = _normalize_internal_url(raw_base_url, "http://product_service:8002")
        if self.base_url.endswith(":8006"):
            self.base_url = self.base_url[:-5] + ":8002"
        self.internal_key = os.getenv("INTERNAL_SERVICE_KEY", "")
        self.timeout = float(os.getenv("UPSTREAM_TIMEOUT", 5))
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with auth."""
        headers = {"Content-Type": "application/json", "Host": "gateway"}
        if self.internal_key:
            headers["X-Internal-Service-Key"] = self.internal_key
            headers["X-Internal-Service"] = "cart_service"
            headers["X-Internal-Token"] = self.internal_key
        return headers
    
    def get_product_snapshot(
        self,
        product_id: str,
        variant_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get product snapshot."""
        try:
            url = f"{self.base_url}/api/v1/catalog/products/{product_id}/"
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, headers=self._get_headers())
                response.raise_for_status()
                data = response.json()
                base_price = data.get("base_price", 0)
                chosen_variant = None
                if variant_id and isinstance(data.get("variants"), list):
                    chosen_variant = next((v for v in data["variants"] if str(v.get("id")) == str(variant_id)), None)
                price = chosen_variant.get("price_override") if chosen_variant and chosen_variant.get("price_override") is not None else base_price
                return {
                    "id": str(data.get("id")),
                    "name": data.get("name", ""),
                    "slug": data.get("slug", ""),
                    "price": price,
                    "sku": (chosen_variant or {}).get("sku"),
                    "brand_name": data.get("brand_name"),
                    "category_name": data.get("category_name"),
                    "thumbnail_url": data.get("thumbnail_url"),
                    "variant_name": (chosen_variant or {}).get("name"),
                    "attributes": data.get("attributes", {}),
                    "status": data.get("status"),
                    "is_active": data.get("is_active", False),
                }
        except Exception as e:
            logger.error(f"Failed to fetch product snapshot: {e}")
            return None
    
    def validate_product_active(
        self,
        product_id: str,
        variant_id: Optional[str] = None
    ) -> bool:
        """Check if product is active."""
        try:
            url = f"{self.base_url}/api/v1/catalog/products/{product_id}/"
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, headers=self._get_headers())
                response.raise_for_status()
                data = response.json()
                return data.get("status") == "active" and bool(data.get("is_active", False))
        except Exception as e:
            logger.error(f"Failed to validate product: {e}")
            return False
    
    def bulk_get_product_snapshots(
        self,
        items: List[Dict[str, str]]
    ) -> Dict[str, Dict[str, Any]]:
        """Bulk fetch product snapshots."""
        snapshots: Dict[str, Dict[str, Any]] = {}
        for item in items:
            product_id = str(item.get("product_id", "")).strip()
            variant_id = item.get("variant_id")
            if not product_id:
                continue
            snap = self.get_product_snapshot(product_id, variant_id)
            if snap:
                key = f"{product_id}#{variant_id or ''}"
                snapshots[key] = snap
        return snapshots


class HttpInventoryServiceClient(InventoryServiceClient):
    """
    HTTP client for inventory_service.
    """
    
    def __init__(self):
        raw_base_url = os.getenv("INVENTORY_SERVICE_URL", "http://inventory_service:8007")
        self.base_url = _normalize_internal_url(raw_base_url, "http://inventory_service:8007")
        self.internal_key = os.getenv("INTERNAL_SERVICE_KEY", "")
        self.timeout = float(os.getenv("UPSTREAM_TIMEOUT", 5))
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with auth."""
        headers = {"Content-Type": "application/json", "Host": "gateway"}
        if self.internal_key:
            headers["X-Internal-Service-Key"] = self.internal_key
            headers["X-Internal-Service"] = "cart_service"
            headers["X-Internal-Token"] = self.internal_key
        return headers
    
    def check_availability(
        self,
        items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Check availability for items."""
        try:
            url = f"{self.base_url}/api/v1/internal/inventory/check_availability/"
            payload = {"items": items}
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, headers=self._get_headers(), json=payload)
                response.raise_for_status()
                
                data = response.json()
                if data.get("success"):
                    payload_data = data.get("data", {}) or {}
                    result_items = payload_data.get("items", []) if isinstance(payload_data, dict) else []
                    all_available = all(bool(item.get("can_reserve")) for item in result_items) if result_items else True
                    return {"available": all_available, "items": result_items}
                return {"available": False, "items": []}
        except Exception as e:
            logger.error(f"Failed to check availability: {e}")
            return {"available": False, "items": []}
    
    def get_product_availability(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get availability for a product."""
        try:
            url = f"{self.base_url}/api/v1/internal/inventory/products/{product_id}/availability/"
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, headers=self._get_headers())
                response.raise_for_status()
                
                data = response.json()
                if data.get("success"):
                    return data.get("data")
                return None
        except Exception as e:
            logger.error(f"Failed to get product availability: {e}")
            return None


# Factory functions for easy dependency injection

def get_product_service_client() -> ProductServiceClient:
    """Get product service client."""
    return HttpProductServiceClient()


def get_inventory_service_client() -> InventoryServiceClient:
    """Get inventory service client."""
    return HttpInventoryServiceClient()
