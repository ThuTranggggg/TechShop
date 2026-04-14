"""
Mock Payment Provider Implementation

For local development and testing without real payment gateway.
"""

from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timedelta
import json
import uuid
import hmac
import hashlib
from urllib.parse import urlencode

from ...domain.entities import Payment
from ...domain.enums import PaymentProvider
from ...domain.value_objects import (
    PaymentProviderResponse,
    CallbackPayload,
)
from .base import BasePaymentProvider, MockPaymentProviderMixin


class MockPaymentProvider(BasePaymentProvider, MockPaymentProviderMixin):
    """
    Mock payment provider for local development.
    
    Simulates payment flow without actual payment gateway.
    Supports success/failure/cancel flows via API calls.
    """

    def __init__(self, webhook_url: str = None, environment: str = "dev"):
        """
        Initialize mock provider.
        
        Args:
            webhook_url: Base URL for webhooks (optional)
            environment: 'dev' or 'test'
        """
        self.webhook_url = webhook_url or "http://localhost:8005"
        self.environment = environment
        self._webhook_secret = "mock-webhook-secret-12345"
        # Store payment states in memory (for demo)
        self._payments: Dict[str, Dict[str, Any]] = {}

    @property
    def provider_name(self) -> str:
        return PaymentProvider.MOCK.value

    def create_payment(self, payment: Payment) -> PaymentProviderResponse:
        """Create mock payment session"""
        try:
            # Generate mock provider payment ID
            provider_payment_id = f"mock_{uuid.uuid4().hex[:16]}"
            client_secret = f"secret_{uuid.uuid4().hex[:16]}"

            # Generate checkout URL (local API endpoint)
            checkout_params = {
                'payment_reference': str(payment.payment_reference),
                'amount': float(payment.amount.amount),
                'currency': payment.amount.currency.value,
            }
            checkout_url = (
                f"{self.webhook_url}/api/v1/mock-payments/"
                f"{payment.payment_reference}/checkout/?{urlencode(checkout_params)}"
            )

            # Store payment in mock state
            self._payments[provider_payment_id] = {
                'payment_reference': str(payment.payment_reference),
                'amount': float(payment.amount.amount),
                'currency': payment.amount.currency.value,
                'status': 'created',
                'created_at': datetime.utcnow().isoformat(),
                'expires_at': (datetime.utcnow() + timedelta(hours=24)).isoformat(),
            }

            return PaymentProviderResponse(
                success=True,
                provider_id=provider_payment_id,
                checkout_url=checkout_url,
                client_secret=client_secret,
                status='created',
                message='Mock payment session created',
                raw_response={
                    'type': 'mock',
                    'payment_id': provider_payment_id,
                    'client_secret': client_secret,
                    'checkout_url': checkout_url,
                }
            )
        except Exception as e:
            return PaymentProviderResponse(
                success=False,
                message=f'Failed to create mock payment: {str(e)}',
                error_code='MOCK_CREATE_ERROR',
            )

    def get_payment_status(
        self,
        provider_payment_id: str,
    ) -> PaymentProviderResponse:
        """Get mock payment status"""
        try:
            if provider_payment_id not in self._payments:
                return PaymentProviderResponse(
                    success=False,
                    message='Payment not found',
                    error_code='NOT_FOUND',
                )

            payment_data = self._payments[provider_payment_id]
            status = payment_data.get('status', 'unknown')

            return PaymentProviderResponse(
                success=True,
                provider_id=provider_payment_id,
                status=status,
                message=f'Payment status: {status}',
                raw_response=payment_data,
            )
        except Exception as e:
            return PaymentProviderResponse(
                success=False,
                message=f'Failed to get payment status: {str(e)}',
                error_code='MOCK_STATUS_ERROR',
            )

    def cancel_payment(
        self,
        provider_payment_id: str,
    ) -> PaymentProviderResponse:
        """Cancel mock payment"""
        try:
            if provider_payment_id not in self._payments:
                return PaymentProviderResponse(
                    success=False,
                    message='Payment not found',
                    error_code='NOT_FOUND',
                )

            self._payments[provider_payment_id]['status'] = 'cancelled'

            return PaymentProviderResponse(
                success=True,
                provider_id=provider_payment_id,
                status='cancelled',
                message='Mock payment cancelled',
                raw_response=self._payments[provider_payment_id],
            )
        except Exception as e:
            return PaymentProviderResponse(
                success=False,
                message=f'Failed to cancel payment: {str(e)}',
                error_code='MOCK_CANCEL_ERROR',
            )

    def capture_payment(
        self,
        provider_payment_id: str,
        amount: Optional[Decimal] = None,
    ) -> PaymentProviderResponse:
        """Capture mock payment"""
        try:
            if provider_payment_id not in self._payments:
                return PaymentProviderResponse(
                    success=False,
                    message='Payment not found',
                    error_code='NOT_FOUND',
                )

            payment_data = self._payments[provider_payment_id]
            payment_data['status'] = 'captured'
            if amount:
                payment_data['captured_amount'] = float(amount)

            return PaymentProviderResponse(
                success=True,
                provider_id=provider_payment_id,
                status='captured',
                message='Mock payment captured',
                raw_response=payment_data,
            )
        except Exception as e:
            return PaymentProviderResponse(
                success=False,
                message=f'Failed to capture payment: {str(e)}',
                error_code='MOCK_CAPTURE_ERROR',
            )

    def refund_payment(
        self,
        provider_payment_id: str,
        amount: Optional[Decimal] = None,
    ) -> PaymentProviderResponse:
        """Refund mock payment"""
        try:
            if provider_payment_id not in self._payments:
                return PaymentProviderResponse(
                    success=False,
                    message='Payment not found',
                    error_code='NOT_FOUND',
                )

            payment_data = self._payments[provider_payment_id]
            payment_data['status'] = 'refunded'
            if amount:
                payment_data['refunded_amount'] = float(amount)

            return PaymentProviderResponse(
                success=True,
                provider_id=provider_payment_id,
                status='refunded',
                message='Mock payment refunded',
                raw_response=payment_data,
            )
        except Exception as e:
            return PaymentProviderResponse(
                success=False,
                message=f'Failed to refund payment: {str(e)}',
                error_code='MOCK_REFUND_ERROR',
            )

    def simulate_payment_success(
        self,
        provider_payment_id: str,
    ) -> PaymentProviderResponse:
        """Simulate successful payment"""
        try:
            if provider_payment_id not in self._payments:
                return PaymentProviderResponse(
                    success=False,
                    message='Payment not found',
                    error_code='NOT_FOUND',
                )

            self._payments[provider_payment_id]['status'] = 'succeeded'
            self._payments[provider_payment_id]['succeeded_at'] = (
                datetime.utcnow().isoformat()
            )

            return PaymentProviderResponse(
                success=True,
                provider_id=provider_payment_id,
                status='succeeded',
                message='Mock payment succeeded',
                raw_response=self._payments[provider_payment_id],
            )
        except Exception as e:
            return PaymentProviderResponse(
                success=False,
                message=f'Failed to simulate success: {str(e)}',
                error_code='MOCK_SIM_SUCCESS_ERROR',
            )

    def simulate_payment_failure(
        self,
        provider_payment_id: str,
        reason: str = "Mock failure",
    ) -> PaymentProviderResponse:
        """Simulate failed payment"""
        try:
            if provider_payment_id not in self._payments:
                return PaymentProviderResponse(
                    success=False,
                    message='Payment not found',
                    error_code='NOT_FOUND',
                )

            self._payments[provider_payment_id]['status'] = 'failed'
            self._payments[provider_payment_id]['failure_reason'] = reason
            self._payments[provider_payment_id]['failed_at'] = (
                datetime.utcnow().isoformat()
            )

            return PaymentProviderResponse(
                success=True,
                provider_id=provider_payment_id,
                status='failed',
                message=f'Mock payment failed: {reason}',
                raw_response=self._payments[provider_payment_id],
            )
        except Exception as e:
            return PaymentProviderResponse(
                success=False,
                message=f'Failed to simulate failure: {str(e)}',
                error_code='MOCK_SIM_FAILURE_ERROR',
            )

    def simulate_payment_cancel(
        self,
        provider_payment_id: str,
    ) -> PaymentProviderResponse:
        """Simulate cancelled payment"""
        try:
            if provider_payment_id not in self._payments:
                return PaymentProviderResponse(
                    success=False,
                    message='Payment not found',
                    error_code='NOT_FOUND',
                )

            self._payments[provider_payment_id]['status'] = 'cancelled'
            self._payments[provider_payment_id]['cancelled_at'] = (
                datetime.utcnow().isoformat()
            )

            return PaymentProviderResponse(
                success=True,
                provider_id=provider_payment_id,
                status='cancelled',
                message='Mock payment cancelled',
                raw_response=self._payments[provider_payment_id],
            )
        except Exception as e:
            return PaymentProviderResponse(
                success=False,
                message=f'Failed to simulate cancel: {str(e)}',
                error_code='MOCK_SIM_CANCEL_ERROR',
            )

    def parse_callback(self, payload: Dict[str, Any]) -> CallbackPayload:
        """Parse mock callback payload"""
        if not payload:
            raise ValueError("Empty callback payload")

        return CallbackPayload(
            provider=PaymentProvider.MOCK,
            event_type=payload.get('event_type', 'payment.status_updated'),
            payment_reference=payload.get('payment_reference', ''),
            provider_payment_id=payload.get('provider_payment_id'),
            status=payload.get('status'),
            amount=Decimal(str(payload.get('amount', 0))),
            currency=payload.get('currency'),
            timestamp=datetime.utcnow(),
            signature=payload.get('signature'),
            raw_payload=payload,
        )

    def webhook_secret(self) -> Optional[str]:
        """Get mock webhook secret"""
        return self._webhook_secret

    def verify_webhook_signature(
        self,
        payload: Dict[str, Any],
        signature: str,
    ) -> bool:
        """
        Verify webhook signature (mock implementation).
        
        In production, verify actual HMAC signature.
        """
        # For mock, always return True in dev mode
        if self.environment == 'dev':
            return True

        # In test mode, verify a simple signature
        payload_str = json.dumps(payload, sort_keys=True)
        expected_signature = hmac.new(
            self._webhook_secret.encode(),
            payload_str.encode(),
            hashlib.sha256,
        ).hexdigest()

        return signature == expected_signature

    def clear_payments(self):
        """Clear all mock payments (for testing)"""
        self._payments.clear()

    def get_mock_payment(self, provider_payment_id: str) -> Optional[Dict]:
        """Get mock payment data (for testing)"""
        return self._payments.get(provider_payment_id)
