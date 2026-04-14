"""
Payment Domain Services

Domain-level services for payment business logic and operations.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Tuple, Dict, Any
from uuid import UUID, uuid4
import random
import string

from .entities import Payment, PaymentTransaction
from .enums import (
    PaymentStatus,
    PaymentTransactionType,
    PaymentTransactionStatus,
    PaymentProvider,
    PaymentMethod,
    Currency,
)
from .value_objects import (
    Money,
    PaymentReference,
    OrderSnapshot,
    PaymentProviderReference,
    CheckoutMetadata,
)


class PaymentNumberGenerator:
    """Generates unique payment reference numbers"""

    @staticmethod
    def generate(prefix: str = "PAY") -> PaymentReference:
        """Generate new payment reference: PAY-YYYYMMDD-XXXXXX"""
        return PaymentReference.generate(prefix=prefix)

    @staticmethod
    def validate_reference(reference: PaymentReference) -> bool:
        """Validate payment reference format"""
        try:
            PaymentReference(str(reference))
            return True
        except ValueError:
            return False


class PaymentValidator:
    """Validates payment creation and state transitions"""

    @staticmethod
    def validate_create_payload(
        order_id: UUID,
        amount: Decimal,
        currency: str,
        provider: str,
        method: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate payment creation payload
        Returns: (is_valid, error_message)
        """
        # Validate amount
        if amount <= 0:
            return False, "Amount must be greater than 0"
        if amount > Decimal("999999999.99"):
            return False, "Amount exceeds maximum allowed"

        # Validate currency
        try:
            Currency(currency)
        except ValueError:
            return False, f"Invalid currency: {currency}"

        # Validate provider
        try:
            PaymentProvider(provider)
        except ValueError:
            return False, f"Invalid provider: {provider}"

        # Validate method
        try:
            PaymentMethod(method)
        except ValueError:
            return False, f"Invalid payment method: {method}"

        # Validate order
        if not order_id:
            return False, "Order ID is required"

        return True, None

    @staticmethod
    def validate_state_transition(
        current_status: PaymentStatus,
        new_status: PaymentStatus,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate payment status transition
        Returns: (is_valid, error_message)
        """
        valid_transitions = {
            PaymentStatus.CREATED: {
                PaymentStatus.PENDING,
                PaymentStatus.FAILED,
                PaymentStatus.CANCELLED,
            },
            PaymentStatus.PENDING: {
                PaymentStatus.REQUIRES_ACTION,
                PaymentStatus.PAID,
                PaymentStatus.FAILED,
                PaymentStatus.CANCELLED,
                PaymentStatus.EXPIRED,
            },
            PaymentStatus.REQUIRES_ACTION: {
                PaymentStatus.PAID,
                PaymentStatus.FAILED,
                PaymentStatus.CANCELLED,
                PaymentStatus.PENDING,
            },
        }

        if current_status not in valid_transitions:
            return False, f"Invalid current status: {current_status}"

        if new_status not in valid_transitions.get(current_status, set()):
            return False, (
                f"Cannot transition from {current_status.value} "
                f"to {new_status.value}"
            )

        return True, None

    @staticmethod
    def validate_callback(
        payment: Payment,
        provider_payment_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate callback safety
        Returns: (is_safe_to_process, error_message)
        """
        # Check if already in terminal state
        if payment.is_terminal():
            return False, (
                f"Payment already in terminal state: {payment.status.value}"
            )

        # Check provider reference if provided
        if provider_payment_id and payment.provider_reference:
            if (
                payment.provider_reference.provider_id != provider_payment_id
            ):
                return False, "Provider payment ID mismatch"

        return True, None


class PaymentStateTransitionService:
    """Manages payment state transitions with validation"""

    @staticmethod
    def transition_to_pending(payment: Payment) -> bool:
        """Transition payment to pending"""
        is_valid, error = PaymentValidator.validate_state_transition(
            payment.status,
            PaymentStatus.PENDING,
        )
        if not is_valid:
            raise ValueError(f"Invalid transition: {error}")
        payment.mark_pending()
        return True

    @staticmethod
    def transition_to_requires_action(payment: Payment) -> bool:
        """Transition payment to requires_action"""
        is_valid, error = PaymentValidator.validate_state_transition(
            payment.status,
            PaymentStatus.REQUIRES_ACTION,
        )
        if not is_valid:
            raise ValueError(f"Invalid transition: {error}")
        payment.mark_requires_action()
        return True

    @staticmethod
    def transition_to_paid(payment: Payment) -> bool:
        """Transition payment to paid"""
        is_valid, error = PaymentValidator.validate_state_transition(
            payment.status,
            PaymentStatus.PAID,
        )
        if not is_valid:
            raise ValueError(f"Invalid transition: {error}")
        payment.mark_paid()
        return True

    @staticmethod
    def transition_to_failed(
        payment: Payment,
        reason: Optional[str] = None,
    ) -> bool:
        """Transition payment to failed"""
        is_valid, error = PaymentValidator.validate_state_transition(
            payment.status,
            PaymentStatus.FAILED,
        )
        if not is_valid:
            raise ValueError(f"Invalid transition: {error}")
        payment.mark_failed(reason)
        return True

    @staticmethod
    def transition_to_cancelled(
        payment: Payment,
        reason: Optional[str] = None,
    ) -> bool:
        """Transition payment to cancelled"""
        is_valid, error = PaymentValidator.validate_state_transition(
            payment.status,
            PaymentStatus.CANCELLED,
        )
        if not is_valid:
            raise ValueError(f"Invalid transition: {error}")
        payment.mark_cancelled(reason)
        return True

    @staticmethod
    def transition_to_expired(payment: Payment) -> bool:
        """Transition payment to expired"""
        is_valid, error = PaymentValidator.validate_state_transition(
            payment.status,
            PaymentStatus.EXPIRED,
        )
        if not is_valid:
            raise ValueError(f"Invalid transition: {error}")
        payment.mark_expired()
        return True


class PaymentCalculationService:
    """Calculates payment-related values"""

    @staticmethod
    def calculate_total_authorized(payment: Payment) -> Money:
        """Calculate total authorized amount from transactions"""
        total = Decimal("0")
        for transaction in payment.get_transactions_by_type(
            PaymentTransactionType.AUTHORIZE
        ):
            if transaction.is_success():
                total += transaction.amount.amount
        return Money(total, payment.amount.currency)

    @staticmethod
    def calculate_total_captured(payment: Payment) -> Money:
        """Calculate total captured amount from transactions"""
        total = Decimal("0")
        for transaction in payment.get_transactions_by_type(
            PaymentTransactionType.CAPTURE
        ):
            if transaction.is_success():
                total += transaction.amount.amount
        return Money(total, payment.amount.currency)

    @staticmethod
    def calculate_total_refunded(payment: Payment) -> Money:
        """Calculate total refunded amount (placeholder)"""
        total = Decimal("0")
        for transaction in payment.get_transactions_by_type(
            PaymentTransactionType.REFUND
        ):
            if transaction.is_success():
                total += transaction.amount.amount
        return Money(total, payment.amount.currency)

    @staticmethod
    def calculate_remaining_amount(payment: Payment) -> Money:
        """Calculate remaining amount to capture/refund"""
        captured = PaymentCalculationService.calculate_total_captured(payment)
        return Money(
            payment.amount.amount - captured.amount,
            payment.amount.currency,
        )

    @staticmethod
    def calculate_payment_expiry(
        created_at: datetime,
        hours: int = 24,
    ) -> datetime:
        """Calculate payment expiry datetime"""
        return created_at + timedelta(hours=hours)

    @staticmethod
    def is_payment_expired(payment: Payment, hours: int = 24) -> bool:
        """Check if payment has expired"""
        expiry = PaymentCalculationService.calculate_payment_expiry(
            payment.created_at,
            hours=hours,
        )
        return datetime.utcnow() > expiry


class PaymentFactory:
    """Factory for creating payment objects"""

    @staticmethod
    def create_payment(
        order: OrderSnapshot,
        amount: Money,
        provider: PaymentProvider,
        method: PaymentMethod,
        description: Optional[str] = None,
        checkout_metadata: Optional[CheckoutMetadata] = None,
    ) -> Payment:
        """Create new payment"""
        payment_reference = PaymentNumberGenerator.generate()

        payment = Payment(
            id=uuid4(),
            payment_reference=payment_reference,
            order=order,
            amount=amount,
            provider=provider,
            method=method,
            status=PaymentStatus.CREATED,
            description=description,
            checkout_metadata=checkout_metadata,
        )

        payment.validate_for_creation()
        return payment

    @staticmethod
    def create_transaction(
        payment_id: UUID,
        transaction_type: PaymentTransactionType,
        amount: Money,
        status: PaymentTransactionStatus = PaymentTransactionStatus.PENDING,
        provider_transaction_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> PaymentTransaction:
        """Create payment transaction"""
        # Generate transaction reference: TRANS-YYYYMMDD-XXXXXX
        date_part = datetime.utcnow().strftime("%Y%m%d")
        random_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        transaction_reference = f"TRANS-{date_part}-{random_part}"

        return PaymentTransaction(
            id=uuid4(),
            payment_id=payment_id,
            transaction_reference=transaction_reference,
            transaction_type=transaction_type,
            status=status,
            amount=amount,
            provider_transaction_id=provider_transaction_id,
            idempotency_key=idempotency_key,
        )
