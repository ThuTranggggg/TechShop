"""
Payment Domain Enumerations

Defines all status types, payment methods, providers, and event types
for the payment domain.
"""

from enum import Enum


class PaymentStatus(str, Enum):
    """
    Payment lifecycle statuses.
    
    Transitions:
    created -> pending
    pending -> requires_action
    pending -> paid
    pending -> failed
    pending -> cancelled
    pending -> expired
    requires_action -> paid
    requires_action -> failed
    requires_action -> cancelled
    """
    CREATED = "created"
    PENDING = "pending"
    REQUIRES_ACTION = "requires_action"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    REFUNDED = "refunded"  # Placeholder for future

    @classmethod
    def choices(cls):
        """Return Django choices format"""
        return [(status.value, status.name) for status in cls]

    def is_terminal(self):
        """Check if payment is in terminal state"""
        terminal_states = {
            self.PAID,
            self.FAILED,
            self.CANCELLED,
            self.EXPIRED,
            self.REFUNDED,
        }
        return self in terminal_states

    def is_success(self):
        """Check if payment is successful"""
        return self == self.PAID

    def is_active(self):
        """Check if payment is still active (not terminal)"""
        return not self.is_terminal()

    def can_retry(self):
        """Check if payment can be retried"""
        return self in {self.FAILED, self.EXPIRED, self.CANCELLED}


class PaymentTransactionType(str, Enum):
    """Payment transaction types for audit trail"""
    CREATE = "create"
    AUTHORIZE = "authorize"
    CAPTURE = "capture"
    CALLBACK = "callback"
    SUCCESS = "success"
    FAIL = "fail"
    CANCEL = "cancel"
    EXPIRE = "expire"
    REFUND = "refund"  # Placeholder

    @classmethod
    def choices(cls):
        return [(t.value, t.name) for t in cls]


class PaymentTransactionStatus(str, Enum):
    """Status of individual transactions/attempts"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @classmethod
    def choices(cls):
        return [(s.value, s.name) for s in cls]


class PaymentMethod(str, Enum):
    """Payment methods supported"""
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    WALLET = "wallet"
    CASH_ON_DELIVERY = "cod"
    QR_CODE = "qr_code"
    MOCK = "mock"  # For development

    @classmethod
    def choices(cls):
        return [(m.value, m.name) for m in cls]


class PaymentProvider(str, Enum):
    """Payment service providers"""
    MOCK = "mock"  # Local development
    VNPAY = "vnpay"  # Vietnamese pay
    MOMO = "momo"  # Vietnamese e-wallet
    STRIPE = "stripe"  # International
    PAYPAL = "paypal"  # International

    @classmethod
    def choices(cls):
        return [(p.value, p.name) for p in cls]


class Currency(str, Enum):
    """Supported currencies"""
    VND = "VND"
    USD = "USD"
    EUR = "EUR"

    @classmethod
    def choices(cls):
        return [(c.value, c.name) for c in cls]


class PaymentEventType(str, Enum):
    """Event types for payment domain events"""
    PAYMENT_CREATED = "payment_created"
    PAYMENT_PENDING = "payment_pending"
    PAYMENT_AUTHORIZED = "payment_authorized"
    PAYMENT_CAPTURED = "payment_captured"
    PAYMENT_SUCCEEDED = "payment_succeeded"
    PAYMENT_FAILED = "payment_failed"
    PAYMENT_CANCELLED = "payment_cancelled"
    PAYMENT_EXPIRED = "payment_expired"
    PAYMENT_REFUNDED = "payment_refunded"
    PAYMENT_CALLBACK_RECEIVED = "payment_callback_received"
    PAYMENT_CALLBACK_PROCESSED = "payment_callback_processed"

    @classmethod
    def choices(cls):
        return [(t.value, t.name) for t in cls]


class PaymentAction(str, Enum):
    """Actions required from user/provider"""
    NONE = "none"
    REDIRECT = "redirect"
    SHOW_QR = "show_qr"
    DISPLAY_FORM = "display_form"
    WAIT = "wait"
    RETRY = "retry"

    @classmethod
    def choices(cls):
        return [(a.value, a.name) for a in cls]
