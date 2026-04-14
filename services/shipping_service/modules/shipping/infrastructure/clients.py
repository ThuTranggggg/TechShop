"""
External Service Clients

Clients for communicating with other services.
"""

import logging
from typing import Optional
from uuid import UUID
import requests
import os

logger = logging.getLogger(__name__)


class OrderServiceClient:
    """Client for communicating with order_service"""

    def __init__(self):
        self.base_url = os.getenv(
            "ORDER_SERVICE_URL",
            "http://order_service:8003/api/v1/internal"
        )
        self.timeout = float(os.getenv("SERVICE_TIMEOUT", "5"))
        self.auth_token = os.getenv("INTERNAL_SERVICE_AUTH_TOKEN", "")

    def _get_headers(self) -> dict:
        """Get request headers"""
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["X-Internal-Service-Key"] = self.auth_token
        return headers

    def notify_shipment_created(
        self,
        order_id: UUID,
        shipment_id: UUID,
        shipment_reference: str,
        tracking_number: str,
        tracking_url: Optional[str] = None,
    ) -> bool:
        """
        Notify order_service that shipment was created.
        
        Returns True if notification succeeded.
        """
        try:
            url = f"{self.base_url}/orders/{order_id}/shipment-created/"
            payload = {
                "shipment_id": str(shipment_id),
                "shipment_reference": shipment_reference,
                "tracking_number": tracking_number,
                "tracking_url": tracking_url,
            }
            
            response = requests.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            
            if response.status_code in (200, 201):
                logger.info(f"Notified order_service shipment created: {order_id}")
                return True
            else:
                logger.warning(
                    f"Failed to notify order_service shipment created: "
                    f"{response.status_code} {response.text}"
                )
                return False
        except requests.Timeout:
            logger.error(f"Timeout notifying order_service shipment created: {order_id}")
            return False
        except Exception as e:
            logger.error(f"Error notifying order_service: {str(e)}")
            return False

    def notify_shipment_status_updated(
        self,
        order_id: UUID,
        shipment_id: UUID,
        shipment_reference: str,
        status: str,
        location: Optional[str] = None,
    ) -> bool:
        """
        Notify order_service of shipment status change.
        
        Returns True if notification succeeded.
        """
        try:
            url = f"{self.base_url}/orders/{order_id}/shipment-status-updated/"
            payload = {
                "shipment_id": str(shipment_id),
                "shipment_reference": shipment_reference,
                "status": status,
                "location": location,
            }
            
            response = requests.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            
            if response.status_code in (200, 201):
                logger.info(f"Notified order_service shipment status: {shipment_reference} -> {status}")
                return True
            else:
                logger.warning(
                    f"Failed to notify order_service shipment status: "
                    f"{response.status_code} {response.text}"
                )
                return False
        except requests.Timeout:
            logger.error(f"Timeout notifying order_service shipment status: {shipment_reference}")
            return False
        except Exception as e:
            logger.error(f"Error notifying order_service shipment status: {str(e)}")
            return False

    def notify_shipment_delivered(
        self,
        order_id: UUID,
        shipment_id: UUID,
        shipment_reference: str,
        delivered_at: str,
    ) -> bool:
        """
        Notify order_service that shipment was delivered.
        
        Returns True if notification succeeded.
        """
        try:
            url = f"{self.base_url}/orders/{order_id}/shipment-delivered/"
            payload = {
                "shipment_id": str(shipment_id),
                "shipment_reference": shipment_reference,
                "delivered_at": delivered_at,
            }
            
            response = requests.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            
            if response.status_code in (200, 201):
                logger.info(f"Notified order_service shipment delivered: {shipment_reference}")
                return True
            else:
                logger.warning(
                    f"Failed to notify order_service shipment delivered: "
                    f"{response.status_code} {response.text}"
                )
                return False
        except requests.Timeout:
            logger.error(f"Timeout notifying order_service shipment delivered: {shipment_reference}")
            return False
        except Exception as e:
            logger.error(f"Error notifying order_service shipment delivered: {str(e)}")
            return False

    def notify_shipment_failed(
        self,
        order_id: UUID,
        shipment_id: UUID,
        shipment_reference: str,
        failure_reason: str,
    ) -> bool:
        """
        Notify order_service of delivery failure.
        
        Returns True if notification succeeded.
        """
        try:
            url = f"{self.base_url}/orders/{order_id}/shipment-failed/"
            payload = {
                "shipment_id": str(shipment_id),
                "shipment_reference": shipment_reference,
                "failure_reason": failure_reason,
            }
            
            response = requests.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            
            if response.status_code in (200, 201):
                logger.info(f"Notified order_service shipment failed: {shipment_reference}")
                return True
            else:
                logger.warning(
                    f"Failed to notify order_service shipment failed: "
                    f"{response.status_code} {response.text}"
                )
                return False
        except requests.Timeout:
            logger.error(f"Timeout notifying order_service shipment failed: {shipment_reference}")
            return False
        except Exception as e:
            logger.error(f"Error notifying order_service shipment failed: {str(e)}")
            return False
