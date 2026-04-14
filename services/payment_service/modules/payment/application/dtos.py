"""
Payment Application DTOs

Data Transfer Objects for API communication.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID


@dataclass
class MoneyDTO:
    """Money representation in API"""
    amount: str  # As string to preserve precision
    currency: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PaymentTransactionDTO:
    """Payment transaction representation"""
    id: str
    payment_id: str
    transaction_reference: str
    transaction_type: str
    status: str
    amount: MoneyDTO
    provider_transaction_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'payment_id': self.payment_id,
            'transaction_reference': self.transaction_reference,
            'transaction_type': self.transaction_type,
            'status': self.status,
            'amount': self.amount.to_dict(),
            'provider_transaction_id': self.provider_transaction_id,
            'error_message': self.error_message,
            'created_at': self.created_at,
        }


@dataclass
class PaymentDetailDTO:
    """Full payment detail"""
    id: str
    payment_reference: str
    order_id: str
    order_number: str
    user_id: Optional[str]
    amount: MoneyDTO
    provider: str
    method: str
    status: str
    provider_payment_id: Optional[str] = None
    checkout_url: Optional[str] = None
    client_secret: Optional[str] = None
    description: Optional[str] = None
    failure_reason: Optional[str] = None
    requested_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    transactions: List[PaymentTransactionDTO] = None
    next_action: Optional[str] = None

    def __post_init__(self):
        if self.transactions is None:
            self.transactions = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'payment_reference': self.payment_reference,
            'order_id': self.order_id,
            'order_number': self.order_number,
            'user_id': self.user_id,
            'amount': self.amount.to_dict(),
            'provider': self.provider,
            'method': self.method,
            'status': self.status,
            'provider_payment_id': self.provider_payment_id,
            'checkout_url': self.checkout_url,
            'client_secret': self.client_secret,
            'description': self.description,
            'failure_reason': self.failure_reason,
            'requested_at': self.requested_at,
            'completed_at': self.completed_at,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'transactions': [t.to_dict() for t in self.transactions] if self.transactions else [],
            'next_action': self.next_action,
        }


@dataclass
class PaymentListItemDTO:
    """Payment summary for list"""
    id: str
    payment_reference: str
    order_id: str
    order_number: str
    amount: MoneyDTO
    status: str
    provider: str
    method: str
    requested_at: Optional[str] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'payment_reference': self.payment_reference,
            'order_id': self.order_id,
            'order_number': self.order_number,
            'amount': self.amount.to_dict(),
            'status': self.status,
            'provider': self.provider,
            'method': self.method,
            'requested_at': self.requested_at,
            'created_at': self.created_at,
        }


@dataclass
class CreatePaymentRequestDTO:
    """Request to create payment"""
    order_id: str
    order_number: str
    amount: Decimal
    currency: str
    provider: str
    method: str
    user_id: Optional[str] = None
    description: Optional[str] = None
    return_url: Optional[str] = None
    cancel_url: Optional[str] = None
    success_url: Optional[str] = None

    def validate(self) -> tuple[bool, Optional[str]]:
        """Validate request"""
        if not self.order_id:
            return False, "order_id is required"
        if not self.order_number:
            return False, "order_number is required"
        if not self.amount or self.amount <= 0:
            return False, "amount must be greater than 0"
        if not self.currency:
            return False, "currency is required"
        if not self.provider:
            return False, "provider is required"
        if not self.method:
            return False, "method is required"
        return True, None


@dataclass
class PaymentStatusDTO:
    """Payment status quick view"""
    payment_reference: str
    order_id: str
    status: str
    amount: MoneyDTO
    provider: str
    provider_payment_id: Optional[str] = None
    next_action: Optional[str] = None
    message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'payment_reference': self.payment_reference,
            'order_id': self.order_id,
            'status': self.status,
            'amount': self.amount.to_dict(),
            'provider': self.provider,
            'provider_payment_id': self.provider_payment_id,
            'next_action': self.next_action,
            'message': self.message,
        }


# Converter functions

def payment_to_detail_dto(payment) -> PaymentDetailDTO:
    """Convert Payment entity to detail DTO"""
    from ..domain.entities import Payment

    transactions = [
        PaymentTransactionDTO(
            id=str(t.id),
            payment_id=str(t.payment_id),
            transaction_reference=t.transaction_reference,
            transaction_type=t.transaction_type.value,
            status=t.status.value,
            amount=MoneyDTO(
                amount=str(t.amount.amount),
                currency=t.amount.currency.value,
            ),
            provider_transaction_id=t.provider_transaction_id,
            error_message=t.error_message,
            created_at=t.created_at.isoformat() if t.created_at else None,
        )
        for t in payment.transactions
    ]

    return PaymentDetailDTO(
        id=str(payment.id),
        payment_reference=str(payment.payment_reference),
        order_id=str(payment.order.order_id),
        order_number=payment.order.order_number,
        user_id=str(payment.order.user_id) if payment.order.user_id else None,
        amount=MoneyDTO(
            amount=str(payment.amount.amount),
            currency=payment.amount.currency.value,
        ),
        provider=payment.provider.value,
        method=payment.method.value,
        status=payment.status.value,
        provider_payment_id=(
            payment.provider_reference.provider_id
            if payment.provider_reference else None
        ),
        checkout_url=(
            payment.checkout_metadata.checkout_url
            if payment.checkout_metadata else None
        ),
        client_secret=(
            payment.checkout_metadata.client_secret
            if payment.checkout_metadata else None
        ),
        description=payment.description,
        failure_reason=payment.failure_reason,
        requested_at=payment.requested_at.isoformat() if payment.requested_at else None,
        completed_at=payment.completed_at.isoformat() if payment.completed_at else None,
        created_at=payment.created_at.isoformat() if payment.created_at else None,
        updated_at=payment.updated_at.isoformat() if payment.updated_at else None,
        transactions=transactions,
        next_action="redirect" if payment.checkout_metadata and payment.checkout_metadata.checkout_url else None,
    )


def payment_to_list_item_dto(payment) -> PaymentListItemDTO:
    """Convert Payment entity to list item DTO"""
    return PaymentListItemDTO(
        id=str(payment.id),
        payment_reference=str(payment.payment_reference),
        order_id=str(payment.order.order_id),
        order_number=payment.order.order_number,
        amount=MoneyDTO(
            amount=str(payment.amount.amount),
            currency=payment.amount.currency.value,
        ),
        status=payment.status.value,
        provider=payment.provider.value,
        method=payment.method.value,
        requested_at=payment.requested_at.isoformat() if payment.requested_at else None,
        created_at=payment.created_at.isoformat() if payment.created_at else None,
    )


def payment_to_status_dto(payment) -> PaymentStatusDTO:
    """Convert Payment to quick status DTO"""
    return PaymentStatusDTO(
        payment_reference=str(payment.payment_reference),
        order_id=str(payment.order.order_id),
        status=payment.status.value,
        amount=MoneyDTO(
            amount=str(payment.amount.amount),
            currency=payment.amount.currency.value,
        ),
        provider=payment.provider.value,
        provider_payment_id=(
            payment.provider_reference.provider_id
            if payment.provider_reference else None
        ),
        next_action="redirect" if payment.checkout_metadata and payment.checkout_metadata.checkout_url else None,
        message=f"Payment {payment.status.value}",
    )
