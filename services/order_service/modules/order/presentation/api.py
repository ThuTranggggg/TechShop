"""
Presentation views for Order API.

DRF views implementing endpoints.
"""

import logging
from uuid import UUID
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.permissions import AllowAny

from ..domain import FulfillmentStatus, OrderStatus
from ..application import (
    GetUserOrdersService, GetOrderDetailService, GetOrderTimelineService,
    CreateOrderFromCartService, HandlePaymentSuccessService,
    HandlePaymentFailureService, CancelOrderService
)
from ..infrastructure import OrderModel, OrderRepositoryImpl, OrderStatusHistoryModel
from ..domain.services import OrderStateTransitionService
from .serializers import (
    OrderDetailSerializer, OrderListItemSerializer, CreateOrderFromCartSerializer,
    OrderTimelineSerializer, CancelOrderSerializer
)
from .permissions import IsAuthenticated, IsInternalService, IsAdminOrStaff

logger = logging.getLogger(__name__)


def _record_status_history(order_id: UUID, from_status: str | None, to_status: str, note: str = "") -> None:
    OrderStatusHistoryModel.objects.create(
        order_id=order_id,
        from_status=from_status,
        to_status=to_status,
        note=note,
        metadata={},
    )


class OrderViewSet(ViewSet):
    """
    Customer order management viewset.
    
    Endpoints:
    - GET /api/v1/orders/ - List user's orders
    - GET /api/v1/orders/{id}/ - Get order detail
    - POST /api/v1/orders/from-cart/ - Create from cart
    - POST /api/v1/orders/{id}/cancel/ - Cancel order
    - GET /api/v1/orders/{id}/timeline/ - Get order timeline
    - GET /api/v1/orders/{id}/status/ - Get order status
    """
    
    def get_permissions(self):
        """Get permissions based on action."""
        if self.action == "health":
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def list(self, request):
        """GET /orders/ - List user's orders."""
        user_id = UUID(request.headers.get("X-User-ID"))
        
        # Pagination
        limit = int(request.query_params.get("limit", 50))
        offset = int(request.query_params.get("offset", 0))
        
        service = GetUserOrdersService()
        order_dtos, total = service.execute(user_id, limit, offset)
        
        serializer = OrderListItemSerializer(order_dtos, many=True)
        
        return Response({
            "success": True,
            "message": "Orders retrieved",
            "data": serializer.data,
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
            }
        }, status=status.HTTP_200_OK)
    
    def retrieve(self, request, pk=None):
        """GET /orders/{id}/ - Get order detail."""
        user_id = UUID(request.headers.get("X-User-ID"))
        order_id = UUID(pk)
        
        service = GetOrderDetailService()
        order_dto = service.execute(order_id)
        
        if not order_dto:
            return Response({
                "success": False,
                "message": "Order not found",
                "errors": {"order_id": [f"Order {order_id} does not exist"]}
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if user owns the order
        if str(order_dto.user_id) != str(user_id):
            return Response({
                "success": False,
                "message": "Not authorized",
                "errors": {"permission": ["You don't have access to this order"]}
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = OrderDetailSerializer(order_dto)
        return Response({
            "success": True,
            "message": "Order retrieved",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=["POST"], url_path="from-cart")
    def create_from_cart(self, request):
        """POST /orders/from-cart/ - Create order from cart."""
        user_id = UUID(request.headers.get("X-User-ID"))
        
        serializer = CreateOrderFromCartSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "success": False,
                "message": "Validation error",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            service = CreateOrderFromCartService()
            order_dto = service.execute(
                user_id=user_id,
                cart_id=serializer.validated_data["cart_id"],
                shipping_address=serializer.validated_data["shipping_address"],
                notes=serializer.validated_data.get("notes") or "",
            )
            
            response_serializer = OrderDetailSerializer(order_dto)
            return Response({
                "success": True,
                "message": "Order created successfully",
                "data": response_serializer.data
            }, status=status.HTTP_201_CREATED)
        
        except ValueError as e:
            logger.warning(f"Order creation validation failed: {e}")
            return Response({
                "success": False,
                "message": "Order creation failed",
                "errors": {"detail": str(e)}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(f"Order creation error: {e}")
            return Response({
                "success": False,
                "message": "Internal server error",
                "errors": {"detail": "Failed to create order"}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=["POST"])
    def cancel(self, request, pk=None):
        """POST /orders/{id}/cancel/ - Cancel order."""
        user_id = UUID(request.headers.get("X-User-ID"))
        order_id = UUID(pk)
        
        # Get order to check ownership
        service = GetOrderDetailService()
        order_dto = service.execute(order_id)
        
        if not order_dto:
            return Response({
                "success": False,
                "message": "Order not found",
                "errors": {"order_id": [str(order_id)]}
            }, status=status.HTTP_404_NOT_FOUND)
        
        if str(order_dto.user_id) != str(user_id):
            return Response({
                "success": False,
                "message": "Not authorized",
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            serializer = CancelOrderSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    "success": False,
                    "message": "Validation error",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            cancel_service = CancelOrderService()
            reason = serializer.validated_data.get("reason", "User cancelled")
            order_dto = cancel_service.execute(order_id, reason)
            
            response_serializer = OrderDetailSerializer(order_dto)
            return Response({
                "success": True,
                "message": "Order cancelled",
                "data": response_serializer.data
            }, status=status.HTTP_200_OK)
        
        except ValueError as e:
            logger.warning(f"Cancel validation failed: {e}")
            return Response({
                "success": False,
                "message": "Cannot cancel order",
                "errors": {"detail": str(e)}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(f"Cancel error: {e}")
            return Response({
                "success": False,
                "message": "Internal server error",
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=["GET"], url_path="timeline")
    def timeline(self, request, pk=None):
        """GET /orders/{id}/timeline/ - Get order timeline."""
        user_id = UUID(request.headers.get("X-User-ID"))
        order_id = UUID(pk)
        
        # Check ownership
        service = GetOrderDetailService()
        order_dto = service.execute(order_id)
        
        if not order_dto:
            return Response({
                "success": False,
                "message": "Order not found",
            }, status=status.HTTP_404_NOT_FOUND)
        
        if str(order_dto.user_id) != str(user_id):
            return Response({
                "success": False,
                "message": "Not authorized",
            }, status=status.HTTP_403_FORBIDDEN)
        
        timeline_service = GetOrderTimelineService()
        timeline_dto = timeline_service.execute(order_id)
        
        if not timeline_dto:
            return Response({
                "success": False,
                "message": "Timeline not found",
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = OrderTimelineSerializer(timeline_dto)
        return Response({
            "success": True,
            "message": "Timeline retrieved",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=["GET"], url_path="status")
    def get_status(self, request, pk=None):
        """GET /orders/{id}/status/ - Get order status."""
        user_id = UUID(request.headers.get("X-User-ID"))
        order_id = UUID(pk)
        
        service = GetOrderDetailService()
        order_dto = service.execute(order_id)
        
        if not order_dto:
            return Response({
                "success": False,
                "message": "Order not found",
            }, status=status.HTTP_404_NOT_FOUND)
        
        if str(order_dto.user_id) != str(user_id):
            return Response({
                "success": False,
                "message": "Not authorized",
            }, status=status.HTTP_403_FORBIDDEN)
        
        return Response({
            "success": True,
            "message": "Status retrieved",
            "data": {
                "order_id": order_dto.id,
                "status": order_dto.status,
                "payment_status": order_dto.payment_status,
                "fulfillment_status": order_dto.fulfillment_status,
            }
        }, status=status.HTTP_200_OK)


class InternalOrderViewSet(ViewSet):
    """
    Internal order management (service-to-service).
    
    Protected by INTERNAL_SERVICE_KEY.
    """
    
    def get_permissions(self):
        """Get permissions."""
        return [IsInternalService()]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_repo = OrderRepositoryImpl()
        self.state_service = OrderStateTransitionService(self.order_repo)
    
    @action(detail=False, methods=["POST"], url_path="create-from-cart")
    def create_from_cart(self, request):
        """POST /internal/orders/create-from-cart/ - Create order (internal)."""
        # Similar to public endpoint but can skip some checks
        payload = request.data
        
        try:
            user_id = UUID(payload.get("user_id"))
            cart_id = UUID(payload.get("cart_id"))
            shipping_address = payload.get("shipping_address", {})
            notes = payload.get("notes")
            
            service = CreateOrderFromCartService()
            order_dto = service.execute(user_id, cart_id, shipping_address, notes)
            
            response_serializer = OrderDetailSerializer(order_dto)
            return Response({
                "success": True,
                "message": "Order created",
                "data": response_serializer.data
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"Internal order creation error: {e}")
            return Response({
                "success": False,
                "message": "Order creation failed",
                "errors": {"detail": str(e)}
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=["POST"], url_path="payment-success")
    def payment_success(self, request, pk=None):
        """POST /internal/orders/{id}/payment-success/ - Mark payment success."""
        order_id = UUID(pk)
        
        try:
            payment_id = UUID(request.data.get("payment_id"))
            service = HandlePaymentSuccessService()
            order_dto = service.execute(order_id, payment_id)
            
            response_serializer = OrderDetailSerializer(order_dto)
            return Response({
                "success": True,
                "message": "Payment success recorded",
                "data": response_serializer.data
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Payment success error: {e}")
            return Response({
                "success": False,
                "message": "Failed to process payment success",
                "errors": {"detail": str(e)}
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=["POST"], url_path="payment-failed")
    def payment_failed(self, request, pk=None):
        """POST /internal/orders/{id}/payment-failed/ - Mark payment failed."""
        order_id = UUID(pk)
        
        try:
            reason = request.data.get("reason", "Payment failed")
            service = HandlePaymentFailureService()
            order_dto = service.execute(order_id, reason)
            
            response_serializer = OrderDetailSerializer(order_dto)
            return Response({
                "success": True,
                "message": "Payment failure recorded",
                "data": response_serializer.data
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Payment failure error: {e}")
            return Response({
                "success": False,
                "message": "Failed to process payment failure",
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def retrieve(self, request, pk=None):
        """GET /internal/orders/{id}/ - Get order (internal)."""
        order_id = UUID(pk)
        
        service = GetOrderDetailService()
        order_dto = service.execute(order_id)
        
        if not order_dto:
            return Response({
                "success": False,
                "message": "Order not found",
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = OrderDetailSerializer(order_dto)
        return Response({
            "success": True,
            "message": "Order retrieved",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=["POST"], url_path="shipment-created")
    def shipment_created(self, request, pk=None):
        """POST /internal/orders/{id}/shipment-created/ - Record shipment creation."""
        order_id = UUID(pk)
        order = self.order_repo.get_by_id(order_id)
        if not order:
            return Response({"success": False, "message": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        shipment_id = request.data.get("shipment_id")
        shipment_reference = request.data.get("shipment_reference")

        try:
            if shipment_id and shipment_reference and not order.shipment_id:
                order.set_shipment_info(UUID(str(shipment_id)), str(shipment_reference))
                self.order_repo.save(order)

            current_status = order.status.value
            if order.status == OrderStatus.PAID:
                self.state_service.transition_to_processing(order)
                _record_status_history(
                    order_id=order_id,
                    from_status=current_status,
                    to_status=OrderStatus.PROCESSING.value,
                    note=f"Shipment created: {shipment_reference or shipment_id}",
                )

            refreshed = GetOrderDetailService().execute(order_id)
            serializer = OrderDetailSerializer(refreshed)
            return Response({"success": True, "message": "Shipment created recorded", "data": serializer.data}, status=status.HTTP_200_OK)
        except Exception as exc:
            logger.error(f"Failed to record shipment_created for {order_id}: {exc}")
            return Response({"success": False, "message": "Failed to record shipment creation", "errors": {"detail": str(exc)}}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["POST"], url_path="shipment-status-updated")
    def shipment_status_updated(self, request, pk=None):
        """POST /internal/orders/{id}/shipment-status-updated/ - Sync shipment state into order."""
        order_id = UUID(pk)
        order = self.order_repo.get_by_id(order_id)
        if not order:
            return Response({"success": False, "message": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        shipment_id = request.data.get("shipment_id")
        shipment_reference = request.data.get("shipment_reference")
        shipping_status = str(request.data.get("status") or "").lower()
        location = request.data.get("location")

        try:
            if shipment_id and shipment_reference and not order.shipment_id:
                order.set_shipment_info(UUID(str(shipment_id)), str(shipment_reference))
                self.order_repo.save(order)

            current_status = order.status.value

            if shipping_status in {"pending_pickup", "picked_up"} and order.status == OrderStatus.PAID:
                self.state_service.transition_to_processing(order)
                _record_status_history(order_id, current_status, OrderStatus.PROCESSING.value, f"Shipment preparing: {shipment_reference or shipment_id}")
            elif shipping_status in {"in_transit", "out_for_delivery"}:
                if order.status == OrderStatus.PAID:
                    self.state_service.transition_to_processing(order)
                    _record_status_history(order_id, current_status, OrderStatus.PROCESSING.value, f"Shipment preparing: {shipment_reference or shipment_id}")
                    current_status = OrderStatus.PROCESSING.value
                    order = self.order_repo.get_by_id(order_id)
                if order and order.status == OrderStatus.PROCESSING:
                    self.state_service.transition_to_shipping(order, shipment_reference=str(shipment_reference or order.shipment_reference or ""))
                    _record_status_history(order_id, current_status, OrderStatus.SHIPPING.value, f"Shipment status updated to {shipping_status}" + (f" @ {location}" if location else ""))
            elif shipping_status in {"failed_delivery", "returned"}:
                OrderModel.objects.filter(id=order_id).update(
                    fulfillment_status=FulfillmentStatus.RETURNED.value,
                    shipment_reference=str(shipment_reference or order.shipment_reference or ""),
                )
                _record_status_history(order_id, order.status.value, order.status.value, f"Shipment status updated to {shipping_status}")
            elif shipping_status == "cancelled":
                OrderModel.objects.filter(id=order_id).update(
                    fulfillment_status=FulfillmentStatus.CANCELLED.value,
                    shipment_reference=str(shipment_reference or order.shipment_reference or ""),
                )
                _record_status_history(order_id, order.status.value, order.status.value, "Shipment cancelled")

            refreshed = GetOrderDetailService().execute(order_id)
            serializer = OrderDetailSerializer(refreshed)
            return Response({"success": True, "message": "Shipment status synced", "data": serializer.data}, status=status.HTTP_200_OK)
        except Exception as exc:
            logger.error(f"Failed to sync shipment status for {order_id}: {exc}")
            return Response({"success": False, "message": "Failed to sync shipment status", "errors": {"detail": str(exc)}}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["POST"], url_path="shipment-delivered")
    def shipment_delivered(self, request, pk=None):
        """POST /internal/orders/{id}/shipment-delivered/ - Mark order delivered."""
        order_id = UUID(pk)
        order = self.order_repo.get_by_id(order_id)
        if not order:
            return Response({"success": False, "message": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            if order.status == OrderStatus.PAID:
                self.state_service.transition_to_processing(order)
                _record_status_history(order_id, OrderStatus.PAID.value, OrderStatus.PROCESSING.value, "Shipment delivery confirmed")
                order = self.order_repo.get_by_id(order_id)
            if order and order.status == OrderStatus.PROCESSING:
                self.state_service.transition_to_shipping(order, shipment_reference=request.data.get("shipment_reference") or order.shipment_reference)
                _record_status_history(order_id, OrderStatus.PROCESSING.value, OrderStatus.SHIPPING.value, "Shipment moved to shipping")
                order = self.order_repo.get_by_id(order_id)
            if order and order.status == OrderStatus.SHIPPING:
                self.state_service.transition_to_delivered(order)
                _record_status_history(order_id, OrderStatus.SHIPPING.value, OrderStatus.DELIVERED.value, f"Shipment delivered at {request.data.get('delivered_at') or 'unknown time'}")

            refreshed = GetOrderDetailService().execute(order_id)
            serializer = OrderDetailSerializer(refreshed)
            return Response({"success": True, "message": "Shipment delivery recorded", "data": serializer.data}, status=status.HTTP_200_OK)
        except Exception as exc:
            logger.error(f"Failed to record shipment delivery for {order_id}: {exc}")
            return Response({"success": False, "message": "Failed to record shipment delivery", "errors": {"detail": str(exc)}}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["POST"], url_path="shipment-failed")
    def shipment_failed(self, request, pk=None):
        """POST /internal/orders/{id}/shipment-failed/ - Mark shipment failure on order timeline."""
        order_id = UUID(pk)
        order = self.order_repo.get_by_id(order_id)
        if not order:
            return Response({"success": False, "message": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        reason = str(request.data.get("failure_reason") or "Shipment failed")
        OrderModel.objects.filter(id=order_id).update(fulfillment_status=FulfillmentStatus.RETURNED.value)
        _record_status_history(order_id, order.status.value, order.status.value, reason)
        refreshed = GetOrderDetailService().execute(order_id)
        serializer = OrderDetailSerializer(refreshed)
        return Response({"success": True, "message": "Shipment failure recorded", "data": serializer.data}, status=status.HTTP_200_OK)


class OperationsOrderViewSet(ViewSet):
    """Admin/staff order operations."""

    def get_permissions(self):
        return [IsAdminOrStaff()]

    def list(self, request):
        """GET /operations/orders/ - List all orders for staff/admin."""
        limit = int(request.query_params.get("limit", 50))
        offset = int(request.query_params.get("offset", 0))
        queryset = OrderModel.objects.all().order_by("-created_at")

        status_filter = request.query_params.get("status")
        payment_status_filter = request.query_params.get("payment_status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if payment_status_filter:
            queryset = queryset.filter(payment_status=payment_status_filter)

        total = queryset.count()
        order_ids = list(queryset.values_list("id", flat=True)[offset : offset + limit])
        service = GetOrderDetailService()
        order_dtos = [service.execute(order_id) for order_id in order_ids]
        serializer = OrderDetailSerializer([dto for dto in order_dtos if dto], many=True)
        return Response(
            {
                "success": True,
                "message": "Operations orders retrieved",
                "data": serializer.data,
                "pagination": {"total": total, "limit": limit, "offset": offset},
            },
            status=status.HTTP_200_OK,
        )

    def retrieve(self, request, pk=None):
        """GET /operations/orders/{id}/ - Retrieve order for staff/admin."""
        order_dto = GetOrderDetailService().execute(UUID(pk))
        if not order_dto:
            return Response({"success": False, "message": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = OrderDetailSerializer(order_dto)
        return Response({"success": True, "message": "Operations order retrieved", "data": serializer.data}, status=status.HTTP_200_OK)
