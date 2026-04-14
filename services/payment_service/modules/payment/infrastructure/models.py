"""
Payment Django ORM Models

Persistence models for Payment and PaymentTransaction aggregates.
"""

from django.db import models
from django.utils import timezone
from uuid import uuid4
import json

from ..domain.enums import (
    PaymentStatus,
    PaymentTransactionType,
    PaymentTransactionStatus,
    PaymentMethod,
    PaymentProvider,
    Currency,
)


class PaymentModel(models.Model):
    """
    Payment persistence model.
    
    Represents a payment request for an order.
    Links to order_service via order_id.
    """
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    payment_reference = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique payment reference: PAY-YYYYMMDD-XXXXXX"
    )
    order_id = models.UUIDField(
        db_index=True,
        help_text="Order ID from order_service"
    )
    order_number = models.CharField(
        max_length=50,
        db_index=True,
        null=True,
        blank=True,
        help_text="Order number snapshot"
    )
    user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User ID from user_service"
    )

    # Amount and Currency
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Payment amount"
    )
    currency = models.CharField(
        max_length=3,
        choices=Currency.choices(),
        default=Currency.VND.value
    )

    # Provider and Method
    provider = models.CharField(
        max_length=20,
        choices=PaymentProvider.choices(),
        default=PaymentProvider.MOCK.value,
        db_index=True
    )
    method = models.CharField(
        max_length=50,
        choices=PaymentMethod.choices(),
        default=PaymentMethod.MOCK.value
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices(),
        default=PaymentStatus.CREATED.value,
        db_index=True
    )

    # Provider references
    provider_payment_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        unique=True,
        help_text="ID from external payment provider"
    )

    # Checkout information
    checkout_url = models.TextField(
        null=True,
        blank=True,
        help_text="URL for user to complete payment"
    )
    client_secret = models.TextField(
        null=True,
        blank=True,
        help_text="Client secret for frontend payment flow"
    )

    # Descriptive fields
    description = models.TextField(
        null=True,
        blank=True,
        help_text="Payment description"
    )
    failure_reason = models.TextField(
        null=True,
        blank=True,
        help_text="Reason for payment failure"
    )

    # Return URLs
    return_url = models.URLField(
        null=True,
        blank=True,
        help_text="URL to return after payment"
    )
    cancel_url = models.URLField(
        null=True,
        blank=True,
        help_text="URL if payment is cancelled"
    )
    success_url = models.URLField(
        null=True,
        blank=True,
        help_text="URL on payment success"
    )

    # Timestamps
    requested_at = models.DateTimeField(
        default=timezone.now,
        help_text="When payment was initiated"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When payment was completed"
    )
    failed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When payment failed"
    )
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When payment was cancelled"
    )
    expired_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When payment expired"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata"
    )

    class Meta:
        db_table = "payment_paymentmodel"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["payment_reference"],
                name="payment_ref_idx"
            ),
            models.Index(
                fields=["order_id"],
                name="order_id_idx"
            ),
            models.Index(
                fields=["user_id"],
                name="user_id_idx"
            ),
            models.Index(
                fields=["status"],
                name="status_idx"
            ),
            models.Index(
                fields=["provider"],
                name="provider_idx"
            ),
            models.Index(
                fields=["order_id", "created_at"],
                name="order_created_idx"
            ),
            models.Index(
                fields=["status", "created_at"],
                name="status_created_idx"
            ),
            models.Index(
                fields=["provider_payment_id"],
                name="provider_payment_id_idx"
            ),
        ]
        verbose_name = "Payment"
        verbose_name_plural = "Payments"

    def __str__(self):
        return f"Payment {self.payment_reference} ({self.status})"

    def is_paid(self):
        return self.status == PaymentStatus.PAID.value

    def is_failed(self):
        return self.status == PaymentStatus.FAILED.value


class PaymentTransactionModel(models.Model):
    """
    Payment transaction/attempt audit model.
    
    Records all calls to provider, callbacks, state changes, etc.
    """
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    payment = models.ForeignKey(
        PaymentModel,
        on_delete=models.CASCADE,
        related_name="transactions",
        help_text="Related payment"
    )
    transaction_reference = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique transaction reference: TRANS-YYYYMMDD-XXXXXX"
    )

    # Transaction type and status
    transaction_type = models.CharField(
        max_length=20,
        choices=PaymentTransactionType.choices(),
        db_index=True
    )
    status = models.CharField(
        max_length=20,
        choices=PaymentTransactionStatus.choices(),
        default=PaymentTransactionStatus.PENDING.value,
        db_index=True
    )

    # Amount
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Transaction amount"
    )
    currency = models.CharField(
        max_length=3,
        choices=Currency.choices(),
        default=Currency.VND.value
    )

    # Provider information
    provider_transaction_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        help_text="ID from payment provider"
    )

    # Payloads
    request_payload = models.JSONField(
        default=dict,
        blank=True,
        help_text="Request payload sent to provider"
    )
    response_payload = models.JSONField(
        default=dict,
        blank=True,
        help_text="Response from provider"
    )
    callback_payload = models.JSONField(
        default=dict,
        blank=True,
        help_text="Callback payload from provider webhook"
    )

    # Error information
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text="Error message if transaction failed"
    )
    error_code = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Error code from provider"
    )

    # Idempotency and deduplication
    idempotency_key = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        help_text="Idempotency key for deduplication"
    )

    # Provider status
    raw_provider_status = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Raw status from provider"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payment_paymenttransactionmodel"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["transaction_reference"],
                name="trans_ref_idx"
            ),
            models.Index(
                fields=["payment_id", "created_at"],
                name="payment_created_idx"
            ),
            models.Index(
                fields=["transaction_type"],
                name="trans_type_idx"
            ),
            models.Index(
                fields=["status"],
                name="trans_status_idx"
            ),
            models.Index(
                fields=["provider_transaction_id"],
                name="provider_trans_id_idx"
            ),
            models.Index(
                fields=["idempotency_key"],
                name="idempotency_key_idx"
            ),
        ]
        verbose_name = "Payment Transaction"
        verbose_name_plural = "Payment Transactions"

    def __str__(self):
        return (
            f"Transaction {self.transaction_reference} "
            f"({self.transaction_type}: {self.status})"
        )

    def is_success(self):
        return self.status == PaymentTransactionStatus.SUCCESS.value

    def is_failed(self):
        return self.status == PaymentTransactionStatus.FAILED.value
