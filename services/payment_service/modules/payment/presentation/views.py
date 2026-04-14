"""
Payment API Views

HTTP API endpoints for payment operations.
"""

import logging
from django.http import JsonResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.request import Request

from common.responses import APIResponse
from ..application.dtos import CreatePaymentRequestDTO, PaymentDetailDTO
from ..application.services import (
    CreatePaymentService,
    GetPaymentDetailService,
    GetPaymentByReferenceService,
    GetPaymentStatusService,
    HandlePaymentCallbackService,
    CancelPaymentService,
    ExpirePaymentService,
)

logger = logging.getLogger(__name__)


class PaymentViewSet(viewsets.ViewSet):
    """Payment API endpoints"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.create_payment_service = CreatePaymentService()
        self.get_detail_service = GetPaymentDetailService()
        self.get_by_reference_service = GetPaymentByReferenceService()
        self.get_status_service = GetPaymentStatusService()
        self.cancel_service = CancelPaymentService()
        self.expire_service = ExpirePaymentService()
        self.callback_service = HandlePaymentCallbackService()

    def create(self, request: Request) -> Response:
        """
        Create payment for order
        
        POST /payments
        
        Request body:
        {
            "order_id": "uuid",
            "order_number": "ORD-001",
            "user_id": "uuid",
            "amount": 100.50,
            "currency": "USD",
            "provider": "stripe",
            "method": "card",
            "description": "Order payment",
            "return_url": "https://...",
            "cancel_url": "https://...",
            "success_url": "https://..."
        }
        """
        try:
            req_data = request.data

            # Create request DTO
            try:
                req_dto = CreatePaymentRequestDTO(
                    order_id=req_data.get("order_id"),
                    order_number=req_data.get("order_number"),
                    user_id=req_data.get("user_id"),
                    amount=req_data.get("amount"),
                    currency=req_data.get("currency", "USD"),
                    provider=req_data.get("provider"),
                    method=req_data.get("method"),
                    description=req_data.get("description"),
                    return_url=req_data.get("return_url"),
                    cancel_url=req_data.get("cancel_url"),
                    success_url=req_data.get("success_url"),
                )
            except TypeError as e:
                logger.error(f"Invalid request data: {str(e)}")
                return Response(
                    APIResponse.error(f"Invalid request: {str(e)}"),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Execute use case
            success, error, payment_dto = self.create_payment_service.execute(
                req_dto
            )

            if not success:
                return Response(
                    APIResponse.error(error or "Failed to create payment"),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(
                APIResponse.success(payment_dto.to_dict()),
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.error(f"Error creating payment: {str(e)}")
            return Response(
                APIResponse.error("Internal server error"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def retrieve(self, request: Request, pk=None) -> Response:
        """
        Get payment detail
        
        GET /payments/{payment_id}
        """
        try:
            payment_dto = self.get_detail_service.execute(pk)

            if not payment_dto:
                return Response(
                    APIResponse.error("Payment not found"),
                    status=status.HTTP_404_NOT_FOUND,
                )

            return Response(APIResponse.success(payment_dto.to_dict()))

        except Exception as e:
            logger.error(f"Error retrieving payment: {str(e)}")
            return Response(
                APIResponse.error("Internal server error"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path="reference/(?P<reference>[\w-]+)")
    def get_by_reference(self, request: Request, reference=None) -> Response:
        """
        Get payment by reference
        
        GET /payments/reference/{reference}
        """
        try:
            payment_dto = self.get_by_reference_service.execute(reference)

            if not payment_dto:
                return Response(
                    APIResponse.error("Payment not found"),
                    status=status.HTTP_404_NOT_FOUND,
                )

            return Response(APIResponse.success(payment_dto.to_dict()))

        except Exception as e:
            logger.error(f"Error getting payment by reference: {str(e)}")
            return Response(
                APIResponse.error("Internal server error"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path="(?P<reference>[\w-]+)/status")
    def get_status(self, request: Request, reference=None) -> Response:
        """
        Get quick payment status
        
        GET /payments/{reference}/status
        """
        try:
            status_dto = self.get_status_service.execute(reference)

            if not status_dto:
                return Response(
                    APIResponse.error("Payment not found"),
                    status=status.HTTP_404_NOT_FOUND,
                )

            return Response(APIResponse.success(status_dto.to_dict()))

        except Exception as e:
            logger.error(f"Error getting payment status: {str(e)}")
            return Response(
                APIResponse.error("Internal server error"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path="(?P<reference>[\w-]+)/cancel")
    def cancel(self, request: Request, reference=None) -> Response:
        """
        Cancel payment
        
        POST /payments/{reference}/cancel
        
        Optional request body:
        {
            "reason": "Optional reason"
        }
        """
        try:
            reason = None
            if isinstance(request.data, dict):
                reason = request.data.get("reason")

            success, error, payment_dto = self.cancel_service.execute(
                reference, reason
            )

            if not success:
                return Response(
                    APIResponse.error(error or "Failed to cancel payment"),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(APIResponse.success(payment_dto.to_dict()))

        except Exception as e:
            logger.error(f"Error cancelling payment: {str(e)}")
            return Response(
                APIResponse.error("Internal server error"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path="(?P<reference>[\w-]+)/expire")
    def expire(self, request: Request, reference=None) -> Response:
        """
        Expire payment
        
        POST /payments/{reference}/expire
        """
        try:
            success, error = self.expire_service.execute(reference)

            if not success:
                return Response(
                    APIResponse.error(error or "Failed to expire payment"),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(
                APIResponse.success({"message": "Payment expired"})
            )

        except Exception as e:
            logger.error(f"Error expiring payment: {str(e)}")
            return Response(
                APIResponse.error("Internal server error"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PaymentWebhookViewSet(viewsets.ViewSet):
    """Payment webhook endpoints"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.callback_service = HandlePaymentCallbackService()

    @action(detail=False, methods=["post"], url_path="(?P<provider>[\w-]+)")
    def handle_callback(self, request: Request, provider=None) -> Response:
        """
        Handle payment provider callback/webhook
        
        POST /webhooks/{provider}
        
        Payload depends on provider (Stripe, Paypal, etc)
        """
        try:
            if not provider:
                return Response(
                    APIResponse.error("Provider not specified"),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            payload = request.data
            if not isinstance(payload, dict):
                payload = {}

            success, error = self.callback_service.execute(provider, payload)

            if not success:
                logger.warning(f"Webhook processing failed: {error}")
                # Always return 200 to provider to acknowledge receipt
                # Failed processing will be retried by provider

            return Response(
                APIResponse.success({"message": "Webhook received"}),
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error handling webhook: {str(e)}")
            # Still return 200 to acknowledge
            return Response(
                APIResponse.success({"message": "Webhook received"}),
                status=status.HTTP_200_OK,
            )
