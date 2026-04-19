"""
Payment Domain Entities

Core aggregates and entities representing payment domain.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from .enums import (
    PaymentStatus,
    PaymentTransactionType,
    PaymentTransactionStatus,
    PaymentMethod,
    PaymentProvider,
    Currency,
)
from .value_objects import (
    Money,
    PaymentReference,
    OrderSnapshot,
    PaymentProviderReference,
    CheckoutMetadata,
)


@dataclass
class PaymentTransaction:
    """
    Represents a single transaction/attempt related to a payment.
    
    Models callbacks, state updates, authorization attempts, captures, etc.
    Immutable after creation.
    """
    id: UUID
    payment_id: UUID
    transaction_reference: str
    transaction_type: PaymentTransactionType
    status: PaymentTransactionStatus
    amount: Money
    provider_transaction_id: Optional[str] = None
    request_payload: Dict[str, Any] = field(default_factory=dict)
    response_payload: Dict[str, Any] = field(default_factory=dict)
    callback_payload: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    idempotency_key: Optional[str] = None
    raw_provider_status: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __str__(self):
        return (
            f"Transaction {self.transaction_reference} "
            f"({self.transaction_type.value}: {self.status.value})"
        )

    def is_success(self) -> bool:
        """Check if transaction succeeded"""
        return self.status == PaymentTransactionStatus.SUCCESS

    def is_failed(self) -> bool:
        """Check if transaction failed"""
        return self.status == PaymentTransactionStatus.FAILED

    def is_terminal(self) -> bool:
        """Check if transaction is in terminal state"""
        return self.status in {
            PaymentTransactionStatus.SUCCESS,
            PaymentTransactionStatus.FAILED,
            PaymentTransactionStatus.CANCELLED,
        }


@dataclass
class Payment:
    """
    Payment aggregate root.
    
    Represents a payment request for an order.
    Manages payment lifecycle, state transitions, and transactions.
    """
    id: UUID
    payment_reference: PaymentReference
    order: OrderSnapshot
    amount: Money
    provider: PaymentProvider
    method: PaymentMethod
    status: PaymentStatus
    provider_reference: Optional[PaymentProviderReference] = None
    checkout_metadata: Optional[CheckoutMetadata] = None
    description: Optional[str] = None
    failure_reason: Optional[str] = None
    requested_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None
    transactions: List[PaymentTransaction] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __str__(self):
        return (
            f"Payment {self.payment_reference} "
            f"({self.amount} for {self.order.order_number}, status={self.status.value})"
        )

    def __post_init__(self):
        """Validate payment on creation"""
        if not self.amount.is_positive():
            raise ValueError(f"Payment amount must be positive: {self.amount}")

    # Status Queries

    def is_pending(self) -> bool:
        """Check if payment is pending"""
        return self.status == PaymentStatus.PENDING

    def is_paid(self) -> bool:
        """Check if payment is paid"""
        return self.status == PaymentStatus.PAID

    def is_failed(self) -> bool:
        """Check if payment is failed"""
        return self.status == PaymentStatus.FAILED

    def is_cancelled(self) -> bool:
        """Check if payment is cancelled"""
        return self.status == PaymentStatus.CANCELLED

    def is_expired(self) -> bool:
        """Check if payment is expired"""
        return self.status == PaymentStatus.EXPIRED

    def is_terminal(self) -> bool:
        """Check if payment is in terminal state"""
        return self.status.is_terminal()

    def is_active(self) -> bool:
        """Check if payment is still active"""
        return self.status.is_active()

    def can_retry(self) -> bool:
        """Check if payment can be retried"""
        return self.status.can_retry()

    # State Transitions

    def mark_pending(self) -> None:
        """Mark payment as pending (waiting for provider/user action)"""
        if self.status not in {PaymentStatus.CREATED, PaymentStatus.PENDING}:
            raise ValueError(
                f"Cannot mark pending from status {self.status.value}"
            )
        self.status = PaymentStatus.PENDING
        self.updated_at = datetime.utcnow()

    def mark_requires_action(self) -> None:
        """Mark payment as requiring action (e.g., redirect, 3DS)"""
        if self.status not in {PaymentStatus.PENDING, PaymentStatus.REQUIRES_ACTION}:
            raise ValueError(
                f"Cannot mark requires_action from status {self.status.value}"
            )
        self.status = PaymentStatus.REQUIRES_ACTION
        self.updated_at = datetime.utcnow()

    def mark_paid(self) -> None:
        """Mark payment as paid/successful"""
        if self.status not in {
            PaymentStatus.PENDING,
            PaymentStatus.REQUIRES_ACTION,
            PaymentStatus.AUTHORIZED,
        }:
            raise ValueError(
                f"Cannot mark paid from status {self.status.value}"
            )
        self.status = PaymentStatus.PAID
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def mark_failed(self, reason: Optional[str] = None) -> None:
        """Mark payment as failed"""
        if self.is_terminal() and not self.can_retry():
            raise ValueError(
                f"Cannot mark failed from terminal status {self.status.value}"
            )
        self.status = PaymentStatus.FAILED
        self.failed_at = datetime.utcnow()
        self.failure_reason = reason
        self.updated_at = datetime.utcnow()

    def mark_cancelled(self, reason: Optional[str] = None) -> None:
        """Mark payment as cancelled"""
        if self.is_terminal():
            raise ValueError(
                f"Cannot cancel payment in terminal status {self.status.value}"
            )
        self.status = PaymentStatus.CANCELLED
        self.cancelled_at = datetime.utcnow()
        self.failure_reason = reason
        self.updated_at = datetime.utcnow()

    def mark_expired(self) -> None:
        """Mark payment as expired"""
        not_expired_statuses = {
            PaymentStatus.CREATED,
            PaymentStatus.PENDING,
            PaymentStatus.REQUIRES_ACTION,
        }
        if self.status not in not_expired_statuses:
            raise ValueError(
                f"Cannot expire payment in status {self.status.value}"
            )
        self.status = PaymentStatus.EXPIRED
        self.expired_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    # Transaction Management

    def add_transaction(self, transaction: PaymentTransaction) -> None:
        """Add transaction to payment history"""
        if transaction.payment_id != self.id:
            raise ValueError("Transaction does not belong to this payment")
        self.transactions.append(transaction)
        self.updated_at = datetime.utcnow()

    def get_transactions_by_type(
        self, transaction_type: PaymentTransactionType
    ) -> List[PaymentTransaction]:
        """Get transactions of specific type"""
        return [
            t for t in self.transactions
            if t.transaction_type == transaction_type
        ]

    def get_last_transaction(self) -> Optional[PaymentTransaction]:
        """Get most recent transaction"""
        return self.transactions[-1] if self.transactions else None

    def get_successful_transactions(self) -> List[PaymentTransaction]:
        """Get all successful transactions"""
        return [
            t for t in self.transactions
            if t.status == PaymentTransactionStatus.SUCCESS
        ]

    def get_failed_transactions(self) -> List[PaymentTransaction]:
        """Get all failed transactions"""
        return [
            t for t in self.transactions
            if t.status == PaymentTransactionStatus.FAILED
        ]

    # Provider Integration

    def set_provider_reference(
        self,
        provider_reference: PaymentProviderReference
    ) -> None:
        """Set external provider reference"""
        self.provider_reference = provider_reference
        self.updated_at = datetime.utcnow()

    def set_checkout_metadata(
        self,
        metadata: CheckoutMetadata
    ) -> None:
        """Set checkout session metadata"""
        self.checkout_metadata = metadata
        self.updated_at = datetime.utcnow()

    # Metadata

    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata key-value"""
        self.metadata[key] = value
        self.updated_at = datetime.utcnow()

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value"""
        return self.metadata.get(key, default)

    # Validation

    def validate_for_creation(self) -> None:
        """Validate payment is ready for creation"""
        if self.amount.amount <= 0:
            raise ValueError(f"Amount must be positive: {self.amount.amount}")
        if self.amount.amount > Decimal("999999999.99"):
            raise ValueError(f"Amount exceeds maximum: {self.amount.amount}")
        if not self.order.order_id or not self.order.order_number:
            raise ValueError("Order snapshot is incomplete")

    def validate_for_capture(self) -> None:
        """Validate payment is ready for capture"""
        if self.status not in {
            PaymentStatus.AUTHORIZED,
            PaymentStatus.PENDING,
        }:
            raise ValueError(
                f"Cannot capture payment in status {self.status.value}"
            )

    # Serialization

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            'id': str(self.id),
            'payment_reference': str(self.payment_reference),
            'order_id': str(self.order.order_id),
            'order_number': self.order.order_number,
            'amount': float(self.amount.amount),
            'currency': self.amount.currency.value,
            'provider': self.provider.value,
            'method': self.method.value,
            'status': self.status.value,
            'provider_payment_id': self.provider_reference.provider_id if self.provider_reference else None,
            'checkout_url': self.checkout_metadata.checkout_url if self.checkout_metadata else None,
            'description': self.description,
            'requested_at': self.requested_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


# Add this as placeholder for PaymentStatus.AUTHORIZED since we reference it above
PaymentStatus.AUTHORIZED = PaymentStatus.REQUIRES_ACTION
