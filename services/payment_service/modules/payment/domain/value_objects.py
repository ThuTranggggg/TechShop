"""
Payment Domain Value Objects

Immutable value objects representing core payment concepts.
"""

from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from .enums import Currency, PaymentProvider, PaymentMethod


@dataclass(frozen=True)
class Money:
    """Immutable money value object with currency"""
    amount: Decimal
    currency: Currency

    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")
        if not isinstance(self.currency, Currency):
            try:
                object.__setattr__(self, 'currency', Currency(self.currency))
            except (ValueError, KeyError):
                raise ValueError(f"Invalid currency: {self.currency}")

    def __str__(self):
        return f"{self.currency.value} {self.amount:,.2f}"

    def __add__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} to {other.currency}")
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract {self.currency} from {other.currency}")
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, factor: float) -> 'Money':
        return Money(self.amount * Decimal(str(factor)), self.currency)

    def is_positive(self) -> bool:
        return self.amount > 0

    def is_zero(self) -> bool:
        return self.amount == 0


@dataclass(frozen=True)
class PaymentReference:
    """
    Immutable, unique payment reference.
    Format: PAY-YYYYMMDD-XXXXXX
    """
    value: str

    def __post_init__(self):
        if not self.value or len(self.value) < 10:
            raise ValueError(f"Invalid payment reference: {self.value}")

    def __str__(self):
        return self.value

    @staticmethod
    def generate(prefix: str = "PAY") -> 'PaymentReference':
        """Generate new payment reference"""
        from datetime import datetime
        import random
        import string

        date_part = datetime.utcnow().strftime("%Y%m%d")
        random_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        value = f"{prefix}-{date_part}-{random_part}"
        return PaymentReference(value)


@dataclass(frozen=True)
class OrderSnapshot:
    """
    Snapshot of order information at payment creation.
    Immutable to preserve historical accuracy.
    """
    order_id: UUID
    order_number: str
    user_id: UUID
    description: Optional[str] = None

    def __str__(self):
        return f"Order {self.order_number} (ID: {self.order_id})"


@dataclass(frozen=True)
class PaymentProviderReference:
    """Reference/ID from external payment provider"""
    provider: PaymentProvider
    provider_id: str
    transaction_id: Optional[str] = None

    def __str__(self):
        return f"{self.provider.value}#{self.provider_id}"


@dataclass(frozen=True)
class CheckoutMetadata:
    """
    Metadata for checkout session.
    Contains URLs and additional context for payment flow.
    """
    checkout_url: Optional[str] = None
    client_secret: Optional[str] = None
    callback_url: Optional[str] = None
    return_url: Optional[str] = None
    cancel_url: Optional[str] = None
    success_url: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = {
            'checkout_url': self.checkout_url,
            'client_secret': self.client_secret,
            'callback_url': self.callback_url,
            'return_url': self.return_url,
            'cancel_url': self.cancel_url,
            'success_url': self.success_url,
        }
        if self.additional_data:
            result.update(self.additional_data)
        return {k: v for k, v in result.items() if v is not None}


@dataclass(frozen=True)
class PaymentProviderResponse:
    """Response from payment provider operation"""
    success: bool
    provider_id: Optional[str] = None
    transaction_id: Optional[str] = None
    checkout_url: Optional[str] = None
    client_secret: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None
    error_code: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None

    def __str__(self):
        status = "success" if self.success else "failed"
        return f"ProviderResponse({status}: {self.message})"


@dataclass(frozen=True)
class CallbackPayload:
    """Immutable callback payload from provider"""
    provider: PaymentProvider
    event_type: str
    payment_reference: str
    provider_payment_id: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    timestamp: Optional[datetime] = None
    signature: Optional[str] = None
    raw_payload: Optional[Dict[str, Any]] = None

    def __str__(self):
        return (
            f"Callback({self.provider.value}: "
            f"{self.event_type} on {self.payment_reference})"
        )


@dataclass(frozen=True)
class PaymentAttemptResult:
    """Result of a payment attempt/transaction"""
    success: bool
    transaction_reference: str
    provider_transaction_id: Optional[str] = None
    status: str = "pending"
    amount: Optional[Decimal] = None
    message: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None

    def is_terminal(self) -> bool:
        """Check if result is terminal (won't change)"""
        return self.status in {"success", "failed", "cancelled"}
