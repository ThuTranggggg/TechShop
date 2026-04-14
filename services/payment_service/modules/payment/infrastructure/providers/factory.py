"""
Payment Provider Factory

Creates appropriate payment provider instances based on configuration.
"""

from typing import Optional
from django.conf import settings

from ...domain.enums import PaymentProvider
from .base import BasePaymentProvider
from .mock_provider import MockPaymentProvider


class PaymentProviderFactory:
    """Factory for creating payment provider instances"""

    _providers = {}

    @classmethod
    def create_provider(
        cls,
        provider_type: str,
        **kwargs
    ) -> BasePaymentProvider:
        """
        Create payment provider instance.
        
        Args:
            provider_type: Type of provider (mock, vnpay, momo, stripe, paypal)
            **kwargs: Additional arguments for provider
            
        Returns:
            Payment provider instance
            
        Raises:
            ValueError: If provider type is not supported
        """
        provider_type = provider_type.lower()

        if provider_type == PaymentProvider.MOCK.value:
            return cls._create_mock_provider(**kwargs)
        elif provider_type == PaymentProvider.VNPAY.value:
            return cls._create_vnpay_provider(**kwargs)
        elif provider_type == PaymentProvider.MOMO.value:
            return cls._create_momo_provider(**kwargs)
        elif provider_type == PaymentProvider.STRIPE.value:
            return cls._create_stripe_provider(**kwargs)
        elif provider_type == PaymentProvider.PAYPAL.value:
            return cls._create_paypal_provider(**kwargs)
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")

    @classmethod
    def get_provider(
        cls,
        provider_type: str,
        use_cache: bool = True,
        **kwargs
    ) -> BasePaymentProvider:
        """
        Get or create provider instance with optional caching.
        
        Args:
            provider_type: Type of provider
            use_cache: Whether to cache provider instance
            **kwargs: Additional arguments
            
        Returns:
            Payment provider instance
        """
        cache_key = f"{provider_type}:{str(kwargs)}"

        if use_cache and cache_key in cls._providers:
            return cls._providers[cache_key]

        provider = cls.create_provider(provider_type, **kwargs)

        if use_cache:
            cls._providers[cache_key] = provider

        return provider

    @classmethod
    def clear_cache(cls):
        """Clear provider cache"""
        cls._providers.clear()

    @staticmethod
    def _create_mock_provider(**kwargs) -> MockPaymentProvider:
        """Create mock provider"""
        webhook_url = kwargs.get(
            'webhook_url',
            getattr(settings, 'PAYMENT_WEBHOOK_URL', 'http://localhost:8005')
        )
        environment = kwargs.get(
            'environment',
            getattr(settings, 'PAYMENT_ENVIRONMENT', 'dev')
        )
        return MockPaymentProvider(
            webhook_url=webhook_url,
            environment=environment
        )

    @staticmethod
    def _create_vnpay_provider(**kwargs) -> BasePaymentProvider:
        """Create VNPay provider (placeholder)"""
        # TODO: Implement VNPay provider
        raise NotImplementedError("VNPay provider not yet implemented")

    @staticmethod
    def _create_momo_provider(**kwargs) -> BasePaymentProvider:
        """Create MoMo provider (placeholder)"""
        # TODO: Implement MoMo provider
        raise NotImplementedError("MoMo provider not yet implemented")

    @staticmethod
    def _create_stripe_provider(**kwargs) -> BasePaymentProvider:
        """Create Stripe provider (placeholder)"""
        # TODO: Implement Stripe provider
        raise NotImplementedError("Stripe provider not yet implemented")

    @staticmethod
    def _create_paypal_provider(**kwargs) -> BasePaymentProvider:
        """Create PayPal provider (placeholder)"""
        # TODO: Implement PayPal provider
        raise NotImplementedError("PayPal provider not yet implemented")


def get_default_provider() -> BasePaymentProvider:
    """Get default payment provider from settings"""
    default_provider = getattr(
        settings,
        'DEFAULT_PAYMENT_PROVIDER',
        PaymentProvider.MOCK.value
    )
    return PaymentProviderFactory.get_provider(default_provider)
