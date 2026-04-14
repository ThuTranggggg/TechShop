"""
Payment Application Services

Use cases and orchestration logic for payment operations.
"""

import logging
from decimal import Decimal
from typing import Optional, Tuple
from uuid import UUID
from django.db import transaction

from ..domain import (
    Payment,
    PaymentRepository,
    PaymentTransactionRepository,
    PaymentStatus,
    PaymentTransactionType,
    PaymentTransactionStatus,
    PaymentProvider,
    PaymentMethod,
    Currency,
    Money,
    OrderSnapshot,
    PaymentFactory,
    PaymentValidator,
    PaymentStateTransitionService,
)
from ..infrastructure.repositories import (
    PaymentRepositoryImpl,
    PaymentTransactionRepositoryImpl,
)
from ..infrastructure.providers import (
    PaymentProviderFactory,
)
from ..infrastructure.clients import OrderServiceClient
from .dtos import (
    CreatePaymentRequestDTO,
    PaymentDetailDTO,
    PaymentStatusDTO,
    payment_to_detail_dto,
    payment_to_list_item_dto,
    payment_to_status_dto,
)

logger = logging.getLogger(__name__)


class CreatePaymentService:
    """Use case: Create payment for order"""

    def __init__(
        self,
        payment_repo: Optional[PaymentRepository] = None,
        provider_factory: Optional[object] = None,
    ):
        self.payment_repo = payment_repo or PaymentRepositoryImpl()
        self.provider_factory = provider_factory or PaymentProviderFactory
        self.transaction_repo = PaymentTransactionRepositoryImpl()

    @transaction.atomic
    def execute(
        self,
        request: CreatePaymentRequestDTO,
    ) -> Tuple[bool, Optional[str], Optional[PaymentDetailDTO]]:
        """
        Create payment for order.
        
        Returns:
            (success, error_message, payment_detail_dto)
        """
        try:
            # Validate request
            is_valid, error = request.validate()
            if not is_valid:
                return False, error, None

            # Validate with domain service
            is_valid, error = PaymentValidator.validate_create_payload(
                order_id=UUID(request.order_id),
                amount=request.amount,
                currency=request.currency,
                provider=request.provider,
                method=request.method,
            )
            if not is_valid:
                return False, error, None

            # Check for existing active payment
            existing = self.payment_repo.get_by_order(UUID(request.order_id))
            if existing and existing.is_active():
                return False, "Order already has an active payment", None

            # Create order snapshot
            order = OrderSnapshot(
                order_id=UUID(request.order_id),
                order_number=request.order_number,
                user_id=UUID(request.user_id) if request.user_id else None,
                description=request.description,
            )

            # Create money
            amount = Money(
                amount=request.amount,
                currency=Currency(request.currency),
            )

            # Create payment entity
            payment = PaymentFactory.create_payment(
                order=order,
                amount=amount,
                provider=PaymentProvider(request.provider),
                method=PaymentMethod(request.method),
                description=request.description,
            )

            # Move to pending
            PaymentStateTransitionService.transition_to_pending(payment)

            # Call provider to create payment
            provider = self.provider_factory.get_provider(request.provider)
            provider_response = provider.create_payment(payment)

            if not provider_response.success:
                payment.mark_failed(f"Provider error: {provider_response.message}")
                self.payment_repo.save(payment)
                return False, provider_response.message, None

            # Update payment with provider reference
            from ..domain.value_objects import (
                PaymentProviderReference,
                CheckoutMetadata,
            )

            if provider_response.provider_id:
                payment.set_provider_reference(
                    PaymentProviderReference(
                        provider=PaymentProvider(request.provider),
                        provider_id=provider_response.provider_id,
                    )
                )

            if provider_response.checkout_url or provider_response.client_secret:
                checkout_meta = CheckoutMetadata(
                    checkout_url=provider_response.checkout_url,
                    client_secret=provider_response.client_secret,
                    return_url=request.return_url,
                    cancel_url=request.cancel_url,
                    success_url=request.success_url,
                )
                payment.set_checkout_metadata(checkout_meta)

            # Create transaction record
            trans = PaymentFactory.create_transaction(
                payment_id=payment.id,
                transaction_type=PaymentTransactionType.CREATE,
                amount=amount,
                status=PaymentTransactionStatus.SUCCESS,
                provider_transaction_id=provider_response.provider_id,
            )
            trans.response_payload = provider_response.raw_response or {}
            payment.add_transaction(trans)

            # Move to requires_action if checkout URL exists
            if provider_response.checkout_url:
                PaymentStateTransitionService.transition_to_requires_action(
                    payment
                )

            # Save payment
            payment = self.payment_repo.save(payment)

            # Return success with DTO
            dto = payment_to_detail_dto(payment)
            return True, None, dto

        except ValueError as e:
            logger.error(f"Validation error in CreatePaymentService: {str(e)}")
            return False, str(e), None
        except Exception as e:
            logger.error(f"Error in CreatePaymentService: {str(e)}")
            return False, "Internal server error", None


class GetPaymentDetailService:
    """Use case: Get payment detail"""

    def __init__(self, payment_repo: Optional[PaymentRepository] = None):
        self.payment_repo = payment_repo or PaymentRepositoryImpl()

    def execute(self, payment_id: str) -> Optional[PaymentDetailDTO]:
        """Get payment detail by ID"""
        try:
            payment = self.payment_repo.get_by_id(UUID(payment_id))
            if not payment:
                return None
            return payment_to_detail_dto(payment)
        except Exception as e:
            logger.error(f"Error in GetPaymentDetailService: {str(e)}")
            return None


class GetPaymentByReferenceService:
    """Use case: Get payment by reference"""

    def __init__(self, payment_repo: Optional[PaymentRepository] = None):
        self.payment_repo = payment_repo or PaymentRepositoryImpl()

    def execute(self, reference: str) -> Optional[PaymentDetailDTO]:
        """Get payment by reference"""
        try:
            payment = self.payment_repo.get_by_reference(reference)
            if not payment:
                return None
            return payment_to_detail_dto(payment)
        except Exception as e:
            logger.error(f"Error in GetPaymentByReferenceService: {str(e)}")
            return None


class GetPaymentStatusService:
    """Use case: Get quick payment status"""

    def __init__(self, payment_repo: Optional[PaymentRepository] = None):
        self.payment_repo = payment_repo or PaymentRepositoryImpl()

    def execute(self, payment_reference: str) -> Optional[PaymentStatusDTO]:
        """Get quick payment status"""
        try:
            payment = self.payment_repo.get_by_reference(payment_reference)
            if not payment:
                return None
            return payment_to_status_dto(payment)
        except Exception as e:
            logger.error(f"Error in GetPaymentStatusService: {str(e)}")
            return None


class HandlePaymentCallbackService:
    """Use case: Handle provider callback"""

    def __init__(
        self,
        payment_repo: Optional[PaymentRepository] = None,
        provider_factory: Optional[object] = None,
    ):
        self.payment_repo = payment_repo or PaymentRepositoryImpl()
        self.provider_factory = provider_factory or PaymentProviderFactory
        self.transaction_repo = PaymentTransactionRepositoryImpl()
        self.order_client = OrderServiceClient()

    @transaction.atomic
    def execute(
        self,
        provider: str,
        payload: dict,
    ) -> Tuple[bool, Optional[str]]:
        """
        Handle payment provider callback.
        
        Returns:
            (success, error_message)
        """
        try:
            # Get provider
            prov = self.provider_factory.get_provider(provider)

            # Parse callback
            try:
                callback = prov.parse_callback(payload)
            except ValueError as e:
                logger.warning(f"Invalid callback payload: {str(e)}")
                return False, "Invalid callback payload"

            # Find payment by reference
            payment = self.payment_repo.get_by_reference(
                callback.payment_reference
            )
            if not payment:
                logger.warning(
                    f"Payment not found for reference: {callback.payment_reference}"
                )
                return False, "Payment not found"

            # Check if payment is in terminal state
            if payment.is_terminal():
                logger.warning(
                    f"Payment already in terminal state: {payment.status.value}"
                )
                # Idempotent: return success if already processed
                return True, None

            # Create transaction record for callback
            trans = PaymentFactory.create_transaction(
                payment_id=payment.id,
                transaction_type=PaymentTransactionType.CALLBACK,
                amount=payment.amount,
            )
            trans.callback_payload = payload
            trans.raw_provider_status = callback.status

            # Handle based on callback status
            if callback.status in {"succeeded", "completed", "paid"}:
                success_result = self._handle_success(payment, trans)
                return success_result
            elif callback.status in {"failed", "error"}:
                return self._handle_failure(payment, trans, callback)
            elif callback.status in {"cancelled"}:
                return self._handle_cancel(payment, trans)
            else:
                # Unknown status, just log and update transaction
                trans.status = PaymentTransactionStatus.PENDING
                payment.add_transaction(trans)
                self.payment_repo.save(payment)
                logger.warning(f"Unknown callback status: {callback.status}")
                return True, None

        except Exception as e:
            logger.error(f"Error in HandlePaymentCallbackService: {str(e)}")
            return False, "Internal server error"

    def _handle_success(
        self,
        payment: Payment,
        transaction: object,
    ) -> Tuple[bool, Optional[str]]:
        """Handle successful payment callback"""
        try:
            # Update transaction
            transaction.status = PaymentTransactionStatus.SUCCESS
            transaction.transaction_type = PaymentTransactionType.SUCCESS
            payment.add_transaction(transaction)

            # Update payment status
            PaymentStateTransitionService.transition_to_paid(payment)

            # Save payment
            payment = self.payment_repo.save(payment)

            # Notify order service
            success = self.order_client.notify_payment_success(
                order_id=payment.order.order_id,
                payment_id=payment.id,
                payment_reference=str(payment.payment_reference),
            )

            if not success:
                logger.warning(
                    f"Failed to notify order_service of payment success: "
                    f"{payment.id}"
                )
                # Don't fail the callback, mark as retryable

            return True, None

        except Exception as e:
            logger.error(f"Error handling payment success: {str(e)}")
            return False, str(e)

    def _handle_failure(
        self,
        payment: Payment,
        transaction: object,
        callback: object,
    ) -> Tuple[bool, Optional[str]]:
        """Handle failed payment callback"""
        try:
            # Update transaction
            transaction.status = PaymentTransactionStatus.FAILED
            transaction.transaction_type = PaymentTransactionType.FAIL
            transaction.error_message = getattr(
                callback, 'message', 'Payment failed'
            )
            payment.add_transaction(transaction)

            # Update payment status
            reason = getattr(callback, 'message', 'Provider declined payment')
            PaymentStateTransitionService.transition_to_failed(
                payment,
                reason=reason,
            )

            # Save payment
            payment = self.payment_repo.save(payment)

            # Notify order service
            success = self.order_client.notify_payment_failed(
                order_id=payment.order.order_id,
                payment_id=payment.id,
                payment_reference=str(payment.payment_reference),
                reason=reason,
            )

            if not success:
                logger.warning(
                    f"Failed to notify order_service of payment failure: "
                    f"{payment.id}"
                )

            return True, None

        except Exception as e:
            logger.error(f"Error handling payment failure: {str(e)}")
            return False, str(e)

    def _handle_cancel(
        self,
        payment: Payment,
        transaction: object,
    ) -> Tuple[bool, Optional[str]]:
        """Handle cancelled payment callback"""
        try:
            # Update transaction
            transaction.status = PaymentTransactionStatus.CANCELLED
            transaction.transaction_type = PaymentTransactionType.CANCEL
            payment.add_transaction(transaction)

            # Update payment status
            PaymentStateTransitionService.transition_to_cancelled(
                payment,
                reason="Cancelled by provider",
            )

            # Save payment
            self.payment_repo.save(payment)

            logger.info(f"Payment cancelled: {payment.id}")
            return True, None

        except Exception as e:
            logger.error(f"Error handling payment cancellation: {str(e)}")
            return False, str(e)


class CancelPaymentService:
    """Use case: Cancel payment"""

    def __init__(
        self,
        payment_repo: Optional[PaymentRepository] = None,
        provider_factory: Optional[object] = None,
    ):
        self.payment_repo = payment_repo or PaymentRepositoryImpl()
        self.provider_factory = provider_factory or PaymentProviderFactory
        self.transaction_repo = PaymentTransactionRepositoryImpl()

    @transaction.atomic
    def execute(
        self,
        payment_reference: str,
        reason: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Optional[PaymentDetailDTO]]:
        """
        Cancel payment.
        
        Returns:
            (success, error_message, payment_detail_dto)
        """
        try:
            # Get payment
            payment = self.payment_repo.get_by_reference(payment_reference)
            if not payment:
                return False, "Payment not found", None

            # Check if can cancel
            if not payment.can_retry() and payment.is_terminal():
                return False, f"Cannot cancel payment in status {payment.status.value}", None

            # Check if already cancelled
            if payment.is_cancelled():
                return True, None, payment_to_detail_dto(payment)

            # Call provider to cancel
            if payment.provider_reference:
                provider = self.provider_factory.get_provider(
                    payment.provider.value
                )
                provider_response = provider.cancel_payment(
                    payment.provider_reference.provider_id
                )
                if not provider_response.success:
                    logger.warning(
                        f"Provider cancel failed: {provider_response.message}"
                    )

            # Update payment status
            PaymentStateTransitionService.transition_to_cancelled(
                payment,
                reason=reason or "User cancelled",
            )

            # Create transaction record
            trans = PaymentFactory.create_transaction(
                payment_id=payment.id,
                transaction_type=PaymentTransactionType.CANCEL,
                amount=payment.amount,
                status=PaymentTransactionStatus.SUCCESS,
            )
            payment.add_transaction(trans)

            # Save payment
            payment = self.payment_repo.save(payment)

            return True, None, payment_to_detail_dto(payment)

        except Exception as e:
            logger.error(f"Error in CancelPaymentService: {str(e)}")
            return False, str(e), None


class ExpirePaymentService:
    """Use case: Expire payment"""

    def __init__(self, payment_repo: Optional[PaymentRepository] = None):
        self.payment_repo = payment_repo or PaymentRepositoryImpl()

    @transaction.atomic
    def execute(
        self,
        payment_reference: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Expire payment.
        
        Returns:
            (success, error_message)
        """
        try:
            # Get payment
            payment = self.payment_repo.get_by_reference(payment_reference)
            if not payment:
                return False, "Payment not found"

            # Check if already expired or terminal
            if payment.is_terminal():
                return True, None

            # Update payment status
            PaymentStateTransitionService.transition_to_expired(payment)

            # Create transaction record
            trans = PaymentFactory.create_transaction(
                payment_id=payment.id,
                transaction_type=PaymentTransactionType.EXPIRE,
                amount=payment.amount,
                status=PaymentTransactionStatus.SUCCESS,
            )
            payment.add_transaction(trans)

            # Save payment
            self.payment_repo.save(payment)

            logger.info(f"Payment expired: {payment_reference}")
            return True, None

        except Exception as e:
            logger.error(f"Error in ExpirePaymentService: {str(e)}")
            return False, str(e)
