"""
Order Service HTTP Client

Internal client for calling order_service APIs.
"""

from typing import Dict, Any, Optional
from uuid import UUID
import httpx
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class OrderServiceClient:
    """
    HTTP client for calling order_service internal APIs.
    
    Notifies order_service about payment status changes.
    """

    def __init__(self):
        """Initialize order client"""
        self.base_url = getattr(
            settings,
            'ORDER_SERVICE_URL',
            'http://order_service:8004'
        )
        self.internal_key = getattr(
            settings,
            'INTERNAL_SERVICE_KEY',
            'internal-key'
        )
        self.timeout = getattr(settings, 'UPSTREAM_TIMEOUT', 5)

    def notify_payment_success(
        self,
        order_id: UUID,
        payment_id: UUID,
        payment_reference: str,
    ) -> bool:
        """
        Notify order_service that payment succeeded.
        
        Args:
            order_id: Order ID
            payment_id: Payment ID
            payment_reference: Payment reference
            
        Returns:
            True if notification sent, False otherwise
        """
        try:
            endpoint = (
                f"{self.base_url}/api/v1/internal/orders/{order_id}/"
                f"payment-success/"
            )
            headers = {
                'X-Internal-Service-Key': self.internal_key,
                'Content-Type': 'application/json',
            }
            payload = {
                'payment_id': str(payment_id),
                'payment_reference': payment_reference,
            }

            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(endpoint, json=payload, headers=headers)
                success = response.status_code in {200, 201}

                if success:
                    logger.info(
                        f"Payment success notified to order_service: "
                        f"order_id={order_id}, payment_id={payment_id}",
                    )
                else:
                    logger.warning(
                        f"Payment success notification failed: {response.text}",
                    )

                return success

        except httpx.RequestError as e:
            logger.error(f"Failed to connect to order_service: {str(e)}")
            return False
        except Exception as e:
            logger.error(
                f"Error notifying payment success: {str(e)}"
            )
            return False

    def notify_payment_failed(
        self,
        order_id: UUID,
        payment_id: UUID,
        payment_reference: str,
        reason: Optional[str] = None,
    ) -> bool:
        """
        Notify order_service that payment failed.
        
        Args:
            order_id: Order ID
            payment_id: Payment ID
            payment_reference: Payment reference
            reason: Reason for failure
            
        Returns:
            True if notification sent, False otherwise
        """
        try:
            endpoint = (
                f"{self.base_url}/api/v1/internal/orders/{order_id}/"
                f"payment-failed/"
            )
            headers = {
                'X-Internal-Service-Key': self.internal_key,
                'Content-Type': 'application/json',
            }
            payload = {
                'payment_id': str(payment_id),
                'payment_reference': payment_reference,
                'reason': reason or 'Payment failed',
            }

            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(endpoint, json=payload, headers=headers)
                success = response.status_code in {200, 201}

                if success:
                    logger.info(
                        f"Payment failed notified to order_service: "
                        f"order_id={order_id}, payment_id={payment_id}",
                    )
                else:
                    logger.warning(
                        f"Payment failed notification failed: {response.text}",
                    )

                return success

        except httpx.RequestError as e:
            logger.error(f"Failed to connect to order_service: {str(e)}")
            return False
        except Exception as e:
            logger.error(
                f"Error notifying payment failure: {str(e)}"
            )
            return False

    def get_order_basic_info(
        self,
        order_id: UUID,
    ) -> Optional[Dict[str, Any]]:
        """
        Get basic order information from order_service (optional).
        
        Args:
            order_id: Order ID
            
        Returns:
            Order data dict or None if not found
        """
        try:
            endpoint = (
                f"{self.base_url}/api/v1/internal/orders/{order_id}/"
            )
            headers = {
                'X-Internal-Service-Key': self.internal_key,
            }

            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(endpoint, headers=headers)

                if response.status_code == 200:
                    return response.json().get('data') or response.json()
                else:
                    logger.warning(
                        f"Order not found in order_service: {order_id}"
                    )
                    return None

        except httpx.RequestError as e:
            logger.error(f"Failed to connect to order_service: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error getting order info: {str(e)}")
            return None
