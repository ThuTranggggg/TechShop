"""
Payment Provider Base Classes

Abstract interfaces for payment providers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from decimal import Decimal

from ...domain.entities import Payment
from ...domain.value_objects import (
    PaymentProviderResponse,
    CallbackPayload,
)


class BasePaymentProvider(ABC):
    """
    Abstract base class for payment providers.
    
    Defines interface for creating, capturing, cancelling payments
    and processing callbacks.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get provider name"""
        pass

    @abstractmethod
    def create_payment(self, payment: Payment) -> PaymentProviderResponse:
        """
        Create payment on provider.
        
        Args:
            payment: Payment entity
            
        Returns:
            PaymentProviderResponse with provider_id, checkout_url, etc.
        """
        pass

    @abstractmethod
    def get_payment_status(
        self,
        provider_payment_id: str,
    ) -> PaymentProviderResponse:
        """
        Get current payment status from provider.
        
        Args:
            provider_payment_id: ID returned from create_payment
            
        Returns:
            PaymentProviderResponse with current status
        """
        pass

    @abstractmethod
    def cancel_payment(
        self,
        provider_payment_id: str,
    ) -> PaymentProviderResponse:
        """
        Cancel payment on provider.
        
        Args:
            provider_payment_id: ID to cancel
            
        Returns:
            PaymentProviderResponse with cancellation result
        """
        pass

    @abstractmethod
    def capture_payment(
        self,
        provider_payment_id: str,
        amount: Optional[Decimal] = None,
    ) -> PaymentProviderResponse:
        """
        Capture authorized payment.
        
        Args:
            provider_payment_id: ID to capture
            amount: Optional partial capture amount
            
        Returns:
            PaymentProviderResponse with capture result
        """
        pass

    @abstractmethod
    def refund_payment(
        self,
        provider_payment_id: str,
        amount: Optional[Decimal] = None,
    ) -> PaymentProviderResponse:
        """
        Refund captured payment.
        
        Args:
            provider_payment_id: ID to refund
            amount: Optional partial refund amount
            
        Returns:
            PaymentProviderResponse with refund result
        """
        pass

    @abstractmethod
    def parse_callback(self, payload: Dict[str, Any]) -> CallbackPayload:
        """
        Parse webhook callback from provider.
        
        Args:
            payload: Raw callback payload
            
        Returns:
            CallbackPayload with normalized data
            
        Raises:
            ValueError: If payload is invalid
        """
        pass

    @abstractmethod
    def webhook_secret(self) -> Optional[str]:
        """Get webhook secret for signature verification"""
        pass

    @abstractmethod
    def verify_webhook_signature(
        self,
        payload: Dict[str, Any],
        signature: str,
    ) -> bool:
        """Verify webhook signature (placeholder)"""
        pass


class MockPaymentProviderMixin:
    """Mixin for mock payment functionality"""

    @abstractmethod
    def simulate_payment_success(
        self,
        provider_payment_id: str,
    ) -> PaymentProviderResponse:
        """Simulate successful payment"""
        pass

    @abstractmethod
    def simulate_payment_failure(
        self,
        provider_payment_id: str,
        reason: str = "Mock failure",
    ) -> PaymentProviderResponse:
        """Simulate failed payment"""
        pass

    @abstractmethod
    def simulate_payment_cancel(
        self,
        provider_payment_id: str,
    ) -> PaymentProviderResponse:
        """Simulate cancelled payment"""
        pass
