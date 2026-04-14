"""
Payment Domain Repository Interfaces

Abstract repository interfaces for payments.
Concrete implementations in infrastructure layer.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID

from .entities import Payment, PaymentTransaction
from .value_objects import PaymentReference


class PaymentRepository(ABC):
    """Abstract repository for Payment aggregate"""

    @abstractmethod
    def save(self, payment: Payment) -> Payment:
        """Save payment to persistence"""
        pass

    @abstractmethod
    def get_by_id(self, payment_id: UUID) -> Optional[Payment]:
        """Get payment by ID"""
        pass

    @abstractmethod
    def get_by_reference(self, reference: PaymentReference) -> Optional[Payment]:
        """Get payment by payment reference"""
        pass

    @abstractmethod
    def get_by_order(self, order_id: UUID) -> Optional[Payment]:
        """Get primary/active payment for order"""
        pass

    @abstractmethod
    def get_payments_by_order(self, order_id: UUID) -> List[Payment]:
        """Get all payments for an order"""
        pass

    @abstractmethod
    def get_by_provider_id(
        self,
        provider_id: str,
        provider: str = None
    ) -> Optional[Payment]:
        """Get payment by provider's payment ID"""
        pass

    @abstractmethod
    def delete(self, payment_id: UUID) -> bool:
        """Delete payment (usually soft delete)"""
        pass

    @abstractmethod
    def update(self, payment: Payment) -> Payment:
        """Update payment"""
        pass


class PaymentTransactionRepository(ABC):
    """Abstract repository for PaymentTransaction"""

    @abstractmethod
    def save(self, transaction: PaymentTransaction) -> PaymentTransaction:
        """Save transaction"""
        pass

    @abstractmethod
    def get_by_id(self, transaction_id: UUID) -> Optional[PaymentTransaction]:
        """Get transaction by ID"""
        pass

    @abstractmethod
    def get_by_reference(self, reference: str) -> Optional[PaymentTransaction]:
        """Get transaction by reference"""
        pass

    @abstractmethod
    def get_by_payment(self, payment_id: UUID) -> List[PaymentTransaction]:
        """Get all transactions for payment"""
        pass

    @abstractmethod
    def get_by_provider_transaction_id(
        self,
        provider_transaction_id: str
    ) -> Optional[PaymentTransaction]:
        """Get transaction by provider's transaction ID"""
        pass

    @abstractmethod
    def get_by_idempotency_key(
        self,
        idempotency_key: str
    ) -> Optional[PaymentTransaction]:
        """Get transaction by idempotency key (for deduplication)"""
        pass

    @abstractmethod
    def get_failed_transactions(
        self,
        payment_id: UUID
    ) -> List[PaymentTransaction]:
        """Get all failed transactions for payment"""
        pass

    @abstractmethod
    def update(self, transaction: PaymentTransaction) -> PaymentTransaction:
        """Update transaction"""
        pass
