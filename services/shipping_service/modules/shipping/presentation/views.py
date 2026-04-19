"""
Shipment REST API Views

HTTP API endpoints.
"""

import logging
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request

from common.responses import APIResponse
from modules.shipping.application import (
    CreateShipmentService,
    CreateShipmentRequestDTO,
    GetShipmentDetailService,
    GetShipmentByReferenceService,
    GetShipmentStatusService,
    GetShipmentTrackingService,
    GetShipmentByOrderService,
    MarkPickedUpService,
    MarkInTransitService,
    MarkOutForDeliveryService,
    MarkDeliveredService,
    MarkFailedDeliveryService,
    MarkReturnedService,
    CancelShipmentService,
    MockAdvanceShipmentStatusService,
)
from modules.shipping.presentation.permissions import (
    IsInternalService,
    IsMockServiceEnabled,
    AllowAny,
    IsAdminOrStaff,
)
from modules.shipping.infrastructure.models import ShipmentModel
from .serializers import (
    CreateShipmentSerializer,
    ShipmentDetailResponseSerializer,
    ShipmentStatusResponseSerializer,
    ShipmentTrackingResponseSerializer,
    AdvanceMockStatusSerializer,
)

logger = logging.getLogger(__name__)


def _normalize_shipping_status(raw_status: str) -> str:
    mapping = {
        "created": "pending",
        "pending_pickup": "pending",
        "picked_up": "preparing",
        "in_transit": "in_transit",
        "out_for_delivery": "in_transit",
        "delivered": "delivered",
        "failed_delivery": "returned",
        "returned": "returned",
        "cancelled": "returned",
    }
    return mapping.get(str(raw_status).lower(), str(raw_status).lower())


class InternalShipmentViewSet(viewsets.ViewSet):
    """Internal API for order_service"""
    
    permission_classes = [IsInternalService]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.create_service = CreateShipmentService()
        self.get_detail_service = GetShipmentDetailService()
        self.get_reference_service = GetShipmentByReferenceService()
        self.get_order_service = GetShipmentByOrderService()
        self.cancel_service = CancelShipmentService()
        self.mark_picked_up_service = MarkPickedUpService()
        self.mark_in_transit_service = MarkInTransitService()
        self.mark_out_for_delivery_service = MarkOutForDeliveryService()
        self.mark_delivered_service = MarkDeliveredService()
        self.mark_failed_delivery_service = MarkFailedDeliveryService()

    def create(self, request: Request) -> Response:
        """
        POST /internal/shipments/
        
        Create shipment for order.
        """
        try:
            serializer = CreateShipmentSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    APIResponse.error("Validation error", errors=serializer.errors),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Convert to DTO
            req_dto = CreateShipmentRequestDTO(
                order_id=serializer.data.get("order_id"),
                order_number=serializer.data.get("order_number"),
                user_id=serializer.data.get("user_id"),
                receiver_name=serializer.data.get("receiver_name"),
                receiver_phone=serializer.data.get("receiver_phone"),
                address_line1=serializer.data.get("address_line1"),
                address_line2=serializer.data.get("address_line2"),
                ward=serializer.data.get("ward"),
                district=serializer.data.get("district"),
                city=serializer.data.get("city"),
                country=serializer.data.get("country", "VN"),
                postal_code=serializer.data.get("postal_code"),
                items=serializer.data.get("items", []),
                service_level=serializer.data.get("service_level", "standard"),
                provider=serializer.data.get("provider", "mock"),
                shipping_fee_amount=serializer.data.get("shipping_fee_amount"),
                currency=serializer.data.get("currency", "VND"),
            )

            success, error, shipment_dto = self.create_service.execute(req_dto)

            if not success:
                return Response(
                    APIResponse.error(error or "Failed to create shipment"),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(
                APIResponse.success(shipment_dto.to_dict()),
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.error(f"Error creating shipment: {str(e)}")
            return Response(
                APIResponse.error("Internal server error"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def retrieve(self, request: Request, pk=None) -> Response:
        """GET /internal/shipments/{id}/"""
        try:
            shipment_dto = self.get_detail_service.execute(pk)
            if not shipment_dto:
                return Response(
                    APIResponse.error("Shipment not found"),
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(APIResponse.success(shipment_dto.to_dict()))
        except Exception as e:
            logger.error(f"Error retrieving shipment: {str(e)}")
            return Response(
                APIResponse.error("Internal server error"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path=r"reference/(?P<shipment_reference>[\w-]+)")
    def get_by_reference(self, request: Request, shipment_reference=None) -> Response:
        """GET /internal/shipments/reference/{reference}/"""
        try:
            shipment_dto = self.get_reference_service.execute(shipment_reference)
            if not shipment_dto:
                return Response(
                    APIResponse.error("Shipment not found"),
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(APIResponse.success(shipment_dto.to_dict()))
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return Response(
                APIResponse.error("Internal server error"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path=r"order/(?P<order_id>[\w-]+)")
    def get_by_order(self, request: Request, order_id=None) -> Response:
        """GET /internal/shipments/order/{order_id}/"""
        try:
            shipment_dto = self.get_order_service.execute(order_id)
            if not shipment_dto:
                return Response(
                    APIResponse.success(None),
                )
            return Response(APIResponse.success(shipment_dto.to_dict()))
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return Response(
                APIResponse.error("Internal server error"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path=r"(?P<shipment_reference>[\w-]+)/cancel")
    def cancel(self, request: Request, shipment_reference=None) -> Response:
        """POST /internal/shipments/{reference}/cancel/"""
        try:
            reason = request.data.get("reason") if isinstance(request.data, dict) else None
            success, error, shipment_dto = self.cancel_service.execute(
                shipment_reference, reason
            )
            if not success:
                return Response(
                    APIResponse.error(error),
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(APIResponse.success(shipment_dto.to_dict()))
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return Response(
                APIResponse.error("Internal server error"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path=r"(?P<shipment_reference>[\w-]+)/mark-picked-up")
    def mark_picked_up(self, request: Request, shipment_reference=None) -> Response:
        """POST /internal/shipments/{reference}/mark-picked-up/"""
        try:
            success, error, shipment_dto = self.mark_picked_up_service.execute(
                shipment_reference
            )
            if not success:
                return Response(
                    APIResponse.error(error),
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(APIResponse.success(shipment_dto.to_dict()))
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return Response(
                APIResponse.error("Internal server error"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path=r"(?P<shipment_reference>[\w-]+)/mark-in-transit")
    def mark_in_transit(self, request: Request, shipment_reference=None) -> Response:
        """POST /internal/shipments/{reference}/mark-in-transit/"""
        try:
            location = request.data.get("location") if isinstance(request.data, dict) else None
            success, error, shipment_dto = self.mark_in_transit_service.execute(
                shipment_reference, location
            )
            if not success:
                return Response(
                    APIResponse.error(error),
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(APIResponse.success(shipment_dto.to_dict()))
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return Response(
                APIResponse.error("Internal server error"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path=r"(?P<shipment_reference>[\w-]+)/mark-out-for-delivery")
    def mark_out_for_delivery(self, request: Request, shipment_reference=None) -> Response:
        """POST /internal/shipments/{reference}/mark-out-for-delivery/"""
        try:
            location = request.data.get("location") if isinstance(request.data, dict) else None
            success, error, shipment_dto = self.mark_out_for_delivery_service.execute(
                shipment_reference, location
            )
            if not success:
                return Response(
                    APIResponse.error(error),
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(APIResponse.success(shipment_dto.to_dict()))
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return Response(
                APIResponse.error("Internal server error"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path=r"(?P<shipment_reference>[\w-]+)/mark-delivered")
    def mark_delivered(self, request: Request, shipment_reference=None) -> Response:
        """POST /internal/shipments/{reference}/mark-delivered/"""
        try:
            location = request.data.get("location") if isinstance(request.data, dict) else None
            success, error, shipment_dto = self.mark_delivered_service.execute(
                shipment_reference, location
            )
            if not success:
                return Response(
                    APIResponse.error(error),
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(APIResponse.success(shipment_dto.to_dict()))
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return Response(
                APIResponse.error("Internal server error"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path=r"(?P<shipment_reference>[\w-]+)/mark-failed-delivery")
    def mark_failed_delivery(self, request: Request, shipment_reference=None) -> Response:
        """POST /internal/shipments/{reference}/mark-failed-delivery/"""
        try:
            reason = request.data.get("reason", "Delivery failed") if isinstance(request.data, dict) else "Delivery failed"
            location = request.data.get("location") if isinstance(request.data, dict) else None
            success, error, shipment_dto = self.mark_failed_delivery_service.execute(
                shipment_reference, reason, location
            )
            if not success:
                return Response(
                    APIResponse.error(error),
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(APIResponse.success(shipment_dto.to_dict()))
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return Response(
                APIResponse.error("Internal server error"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PublicShipmentViewSet(viewsets.ViewSet):
    """Public API for customer tracking"""
    
    permission_classes = [AllowAny]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.get_tracking_service = GetShipmentTrackingService()
        self.get_status_service = GetShipmentStatusService()
        self.get_reference_service = GetShipmentByReferenceService()

    @action(detail=False, methods=["get"], url_path=r"(?P<shipment_reference>[\w-]+)/tracking")
    def get_tracking(self, request: Request, shipment_reference=None) -> Response:
        """GET /shipments/{reference}/tracking/"""
        try:
            tracking_dto = self.get_tracking_service.execute(shipment_reference)
            if not tracking_dto:
                return Response(
                    APIResponse.error("Shipment not found"),
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(APIResponse.success(tracking_dto.to_dict()))
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return Response(
                APIResponse.error("Internal server error"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path=r"(?P<shipment_reference>[\w-]+)/status")
    def get_status(self, request: Request, shipment_reference=None) -> Response:
        """GET /shipments/{reference}/status/"""
        try:
            status_dto = self.get_status_service.execute(shipment_reference)
            if not status_dto:
                return Response(
                    APIResponse.error("Shipment not found"),
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(APIResponse.success(status_dto.to_dict()))
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return Response(
                APIResponse.error("Internal server error"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def retrieve(self, request: Request, pk=None) -> Response:
        """GET /shipments/{reference}/"""
        try:
            shipment_dto = self.get_reference_service.execute(pk)
            if not shipment_dto:
                return Response(
                    APIResponse.error("Shipment not found"),
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(APIResponse.success(shipment_dto.to_dict()))
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return Response(
                APIResponse.error("Internal server error"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class OperationsShipmentViewSet(viewsets.ViewSet):
    """Staff/admin operational shipment endpoints."""

    permission_classes = [IsAdminOrStaff]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.get_order_service = GetShipmentByOrderService()
        self.mark_picked_up_service = MarkPickedUpService()
        self.mark_in_transit_service = MarkInTransitService()
        self.mark_out_for_delivery_service = MarkOutForDeliveryService()
        self.mark_delivered_service = MarkDeliveredService()
        self.mark_failed_delivery_service = MarkFailedDeliveryService()
        self.mark_returned_service = MarkReturnedService()
        self.advance_service = MockAdvanceShipmentStatusService()

    @action(detail=False, methods=["get"], url_path=r"order/(?P<order_id>[\w-]+)")
    def get_by_order(self, request: Request, order_id=None) -> Response:
        """GET /operations/shipments/order/{order_id}/"""
        try:
            shipment_dto = self.get_order_service.execute(order_id)
            if not shipment_dto:
                return Response(APIResponse.error("Shipment not found"), status=status.HTTP_404_NOT_FOUND)

            payload = shipment_dto.to_dict()
            payload["normalized_status"] = _normalize_shipping_status(payload.get("status", ""))
            return Response(APIResponse.success(payload))
        except Exception as e:
            logger.error(f"Error retrieving shipment by order: {str(e)}")
            return Response(APIResponse.error("Internal server error"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["patch"], url_path=r"order/(?P<order_id>[\w-]+)/status")
    def update_by_order_status(self, request: Request, order_id=None) -> Response:
        """PATCH /operations/shipments/order/{order_id}/status/"""
        try:
            shipment_dto = self.get_order_service.execute(order_id)
            if not shipment_dto:
                return Response(APIResponse.error("Shipment not found"), status=status.HTTP_404_NOT_FOUND)

            requested_status = str((request.data or {}).get("status") or "").lower()
            location = (request.data or {}).get("location")
            reason = (request.data or {}).get("reason", "Manual operations update")
            shipment_reference = shipment_dto.shipment_reference

            if requested_status == "pending":
                return Response(
                    APIResponse.success(
                        {
                            **shipment_dto.to_dict(),
                            "normalized_status": _normalize_shipping_status(shipment_dto.status),
                        }
                    )
                )

            if requested_status == "preparing":
                current_status = shipment_dto.status
                if current_status == "pending_pickup":
                    success, error, updated = self.mark_picked_up_service.execute(shipment_reference)
                elif current_status == "created":
                    success, error, updated = self.advance_service.execute(shipment_reference, "pending_pickup")
                    if success:
                        success, error, updated = self.mark_picked_up_service.execute(shipment_reference)
                else:
                    updated = shipment_dto
                    success, error = True, None
            elif requested_status == "in_transit":
                success, error, updated = self.mark_in_transit_service.execute(shipment_reference, location=location)
            elif requested_status == "delivered":
                shipment = ShipmentModel.objects.get(shipment_reference=shipment_reference)
                success, error, updated = True, None, shipment_dto
                if shipment.status == "created":
                    success, error, updated = self.advance_service.execute(shipment_reference, "pending_pickup")
                    shipment = ShipmentModel.objects.get(shipment_reference=shipment_reference)
                if success and shipment.status == "pending_pickup":
                    success, error, updated = self.mark_picked_up_service.execute(shipment_reference)
                    shipment = ShipmentModel.objects.get(shipment_reference=shipment_reference)
                if success and shipment.status == "picked_up":
                    success, error, updated = self.mark_in_transit_service.execute(shipment_reference, location=location)
                    shipment = ShipmentModel.objects.get(shipment_reference=shipment_reference)
                if success and shipment.status == "in_transit":
                    success, error, updated = self.mark_out_for_delivery_service.execute(shipment_reference, location=location)
                    shipment = ShipmentModel.objects.get(shipment_reference=shipment_reference)
                if success and shipment.status == "out_for_delivery":
                    success, error, updated = self.mark_delivered_service.execute(shipment_reference, location=location)
            elif requested_status == "returned":
                shipment = ShipmentModel.objects.get(shipment_reference=shipment_reference)
                if shipment.status in {"in_transit", "out_for_delivery"}:
                    self.mark_failed_delivery_service.execute(shipment_reference, reason=reason, location=location)
                success, error, updated = self.mark_returned_service.execute(shipment_reference, location=location)
            else:
                return Response(APIResponse.error("Invalid status"), status=status.HTTP_400_BAD_REQUEST)

            if not success:
                return Response(APIResponse.error(error or "Status update failed"), status=status.HTTP_400_BAD_REQUEST)

            payload = updated.to_dict()
            payload["normalized_status"] = _normalize_shipping_status(payload.get("status", ""))
            return Response(APIResponse.success(payload))
        except Exception as e:
            logger.error(f"Error updating shipment by order status: {str(e)}")
            return Response(APIResponse.error("Internal server error"), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MockShipmentViewSet(viewsets.ViewSet):
    """Mock shipment APIs for development"""
    
    permission_classes = [IsMockServiceEnabled]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.advance_service = MockAdvanceShipmentStatusService()

    @action(detail=False, methods=["post"], url_path=r"(?P<shipment_reference>[\w-]+)/advance")
    def advance_status(self, request: Request, shipment_reference=None) -> Response:
        """POST /mock-shipments/{reference}/advance/"""
        try:
            serializer = AdvanceMockStatusSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    APIResponse.error("Validation error", errors=serializer.errors),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            success, error, shipment_dto = self.advance_service.execute(
                shipment_reference,
                serializer.data.get("target_status"),
            )
            if not success:
                return Response(
                    APIResponse.error(error),
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(APIResponse.success(shipment_dto.to_dict()))
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return Response(
                APIResponse.error("Internal server error"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
