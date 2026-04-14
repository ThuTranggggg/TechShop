"""
Payment Infrastructure Repositories

Concrete implementations of domain repositories using Django ORM.
"""

from typing import Optional, List
from uuid import UUID

from ..domain.repositories import (
    PaymentRepository,
    PaymentTransactionRepository,
)
from ..domain.entities import Payment, PaymentTransaction
from ..domain.enums import (
    PaymentStatus,
    PaymentTransactionType,
    PaymentTransactionStatus,
    Currency,
)
from ..domain.value_objects import (
    Money,
    PaymentReference,
    OrderSnapshot,
    PaymentProviderReference,
)
from .models import PaymentModel, PaymentTransactionModel


class PaymentRepositoryImpl(PaymentRepository):
    """Concrete payment repository using Django ORM"""

    def save(self, payment: Payment) -> Payment:
        """Save or update payment"""
        model, created = PaymentModel.objects.update_or_create(
            id=payment.id,
            defaults={
                'payment_reference': str(payment.payment_reference),
                'order_id': payment.order.order_id,
                'order_number': payment.order.order_number,
                'user_id': payment.order.user_id,
                'amount': payment.amount.amount,
                'currency': payment.amount.currency.value,
                'provider': payment.provider.value,
                'method': payment.method.value,
                'status': payment.status.value,
                'provider_payment_id': (
                    payment.provider_reference.provider_id
                    if payment.provider_reference else None
                ),
                'checkout_url': (
                    payment.checkout_metadata.checkout_url
                    if payment.checkout_metadata else None
                ),
                'client_secret': (
                    payment.checkout_metadata.client_secret
                    if payment.checkout_metadata else None
                ),
                'description': payment.description,
                'failure_reason': payment.failure_reason,
                'requested_at': payment.requested_at,
                'completed_at': payment.completed_at,
                'failed_at': payment.failed_at,
                'cancelled_at': payment.cancelled_at,
                'expired_at': payment.expired_at,
                'metadata': payment.metadata,
                'updated_at': payment.updated_at,
            }
        )
        return self._model_to_entity(model)

    def get_by_id(self, payment_id: UUID) -> Optional[Payment]:
        """Get payment by ID"""
        try:
            model = PaymentModel.objects.get(id=payment_id)
            return self._model_to_entity(model)
        except PaymentModel.DoesNotExist:
            return None

    def get_by_reference(self, reference: PaymentReference) -> Optional[Payment]:
        """Get payment by reference"""
        try:
            model = PaymentModel.objects.get(
                payment_reference=str(reference)
            )
            return self._model_to_entity(model)
        except PaymentModel.DoesNotExist:
            return None

    def get_by_order(self, order_id: UUID) -> Optional[Payment]:
        """Get primary/active payment for order"""
        try:
            model = PaymentModel.objects.filter(
                order_id=order_id,
                status__in=[
                    PaymentStatus.CREATED.value,
                    PaymentStatus.PENDING.value,
                    PaymentStatus.REQUIRES_ACTION.value,
                ]
            ).latest('created_at')
            return self._model_to_entity(model)
        except PaymentModel.DoesNotExist:
            return None

    def get_payments_by_order(self, order_id: UUID) -> List[Payment]:
        """Get all payments for an order"""
        models = PaymentModel.objects.filter(order_id=order_id).order_by(
            '-created_at'
        )
        return [self._model_to_entity(m) for m in models]

    def get_by_provider_id(
        self,
        provider_id: str,
        provider: str = None,
    ) -> Optional[Payment]:
        """Get payment by provider's payment ID"""
        try:
            query = {'provider_payment_id': provider_id}
            if provider:
                query['provider'] = provider
            model = PaymentModel.objects.get(**query)
            return self._model_to_entity(model)
        except PaymentModel.DoesNotExist:
            return None

    def delete(self, payment_id: UUID) -> bool:
        """Delete payment (soft delete via status)"""
        try:
            payment = self.get_by_id(payment_id)
            if payment:
                payment.mark_cancelled("Deleted")
                self.save(payment)
                return True
            return False
        except Exception:
            return False

    def update(self, payment: Payment) -> Payment:
        """Update payment"""
        return self.save(payment)

    def _model_to_entity(self, model: PaymentModel) -> Payment:
        """Convert ORM model to domain entity"""
        # Reconstruct transactions
        transaction_models = PaymentTransactionModel.objects.filter(
            payment_id=model.id
        ).order_by('created_at')
        transactions = [
            self._transaction_model_to_entity(tm)
            for tm in transaction_models
        ]

        # Reconstruct provider reference
        provider_reference = None
        if model.provider_payment_id:
            provider_reference = PaymentProviderReference(
                provider=model.provider,
                provider_id=model.provider_payment_id,
            )

        # Reconstruct money
        amount = Money(
            amount=model.amount,
            currency=Currency(model.currency),
        )

        # Reconstruct order snapshot
        order = OrderSnapshot(
            order_id=model.order_id,
            order_number=model.order_number or "",
            user_id=model.user_id,
        )

        # Create entity
        payment = Payment(
            id=model.id,
            payment_reference=PaymentReference(model.payment_reference),
            order=order,
            amount=amount,
            provider=model.provider,
            method=model.method,
            status=PaymentStatus(model.status),
            provider_reference=provider_reference,
            description=model.description,
            failure_reason=model.failure_reason,
            requested_at=model.requested_at,
            completed_at=model.completed_at,
            failed_at=model.failed_at,
            cancelled_at=model.cancelled_at,
            expired_at=model.expired_at,
            transactions=transactions,
            metadata=model.metadata or {},
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
        return payment

    @staticmethod
    def _transaction_model_to_entity(
        model: PaymentTransactionModel,
    ) -> PaymentTransaction:
        """Convert transaction ORM model to domain entity"""
        amount = Money(
            amount=model.amount,
            currency=Currency(model.currency),
        )

        return PaymentTransaction(
            id=model.id,
            payment_id=model.payment_id,
            transaction_reference=model.transaction_reference,
            transaction_type=PaymentTransactionType(model.transaction_type),
            status=PaymentTransactionStatus(model.status),
            amount=amount,
            provider_transaction_id=model.provider_transaction_id,
            request_payload=model.request_payload or {},
            response_payload=model.response_payload or {},
            callback_payload=model.callback_payload or {},
            error_message=model.error_message,
            error_code=model.error_code,
            idempotency_key=model.idempotency_key,
            raw_provider_status=model.raw_provider_status,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class PaymentTransactionRepositoryImpl(PaymentTransactionRepository):
    """Concrete payment transaction repository using Django ORM"""

    def save(self, transaction: PaymentTransaction) -> PaymentTransaction:
        """Save transaction"""
        model, created = PaymentTransactionModel.objects.update_or_create(
            id=transaction.id,
            defaults={
                'payment_id': transaction.payment_id,
                'transaction_reference': transaction.transaction_reference,
                'transaction_type': transaction.transaction_type.value,
                'status': transaction.status.value,
                'amount': transaction.amount.amount,
                'currency': transaction.amount.currency.value,
                'provider_transaction_id': transaction.provider_transaction_id,
                'request_payload': transaction.request_payload,
                'response_payload': transaction.response_payload,
                'callback_payload': transaction.callback_payload,
                'error_message': transaction.error_message,
                'error_code': transaction.error_code,
                'idempotency_key': transaction.idempotency_key,
                'raw_provider_status': transaction.raw_provider_status,
            }
        )
        return PaymentRepositoryImpl._transaction_model_to_entity(model)

    def get_by_id(self, transaction_id: UUID) -> Optional[PaymentTransaction]:
        """Get transaction by ID"""
        try:
            model = PaymentTransactionModel.objects.get(id=transaction_id)
            return PaymentRepositoryImpl._transaction_model_to_entity(model)
        except PaymentTransactionModel.DoesNotExist:
            return None

    def get_by_reference(self, reference: str) -> Optional[PaymentTransaction]:
        """Get transaction by reference"""
        try:
            model = PaymentTransactionModel.objects.get(
                transaction_reference=reference
            )
            return PaymentRepositoryImpl._transaction_model_to_entity(model)
        except PaymentTransactionModel.DoesNotExist:
            return None

    def get_by_payment(self, payment_id: UUID) -> List[PaymentTransaction]:
        """Get all transactions for payment"""
        models = PaymentTransactionModel.objects.filter(
            payment_id=payment_id
        ).order_by('created_at')
        return [
            PaymentRepositoryImpl._transaction_model_to_entity(m)
            for m in models
        ]

    def get_by_provider_transaction_id(
        self,
        provider_transaction_id: str,
    ) -> Optional[PaymentTransaction]:
        """Get transaction by provider's transaction ID"""
        try:
            model = PaymentTransactionModel.objects.get(
                provider_transaction_id=provider_transaction_id
            )
            return PaymentRepositoryImpl._transaction_model_to_entity(model)
        except PaymentTransactionModel.DoesNotExist:
            return None

    def get_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> Optional[PaymentTransaction]:
        """Get transaction by idempotency key"""
        try:
            model = PaymentTransactionModel.objects.get(
                idempotency_key=idempotency_key
            )
            return PaymentRepositoryImpl._transaction_model_to_entity(model)
        except PaymentTransactionModel.DoesNotExist:
            return None

    def get_failed_transactions(
        self,
        payment_id: UUID,
    ) -> List[PaymentTransaction]:
        """Get all failed transactions for payment"""
        models = PaymentTransactionModel.objects.filter(
            payment_id=payment_id,
            status=PaymentTransactionStatus.FAILED.value,
        ).order_by('created_at')
        return [
            PaymentRepositoryImpl._transaction_model_to_entity(m)
            for m in models
        ]

    def update(self, transaction: PaymentTransaction) -> PaymentTransaction:
        """Update transaction"""
        return self.save(transaction)
