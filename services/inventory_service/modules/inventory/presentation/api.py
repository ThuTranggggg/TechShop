"""
API views for Inventory service.

Contains viewsets and APIViews for inventory operations.
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request
from uuid import UUID

logger = logging.getLogger(__name__)

from common.responses import success_response, error_response
from ..application.services import InventoryApplicationService
from ..application.dtos import (
    CreateStockItemDTO,
    UpdateStockItemDTO,
    StockInDTO,
    StockOutDTO,
    AdjustStockDTO,
    CreateReservationDTO,
    CheckAvailabilityItemDTO,
)
from ..infrastructure.repositories import (
    DjangoStockItemRepository,
    DjangoStockReservationRepository,
    DjangoStockMovementRepository,
)
from .serializers import (
    StockItemSerializer,
    CreateStockItemSerializer,
    UpdateStockItemSerializer,
    StockInSerializer,
    StockOutSerializer,
    AdjustStockSerializer,
    StockMovementSerializer,
    StockReservationDetailSerializer,
    CreateReservationSerializer,
    CheckAvailabilitySerializer,
    AvailabilityResultSerializer,
    InventorySummarySerializer,
)
from .permissions import IsInternal, IsAdminOrStaff


def get_inventory_service() -> InventoryApplicationService:
    """Factory function to get inventory application service."""
    return InventoryApplicationService(
        stock_item_repo=DjangoStockItemRepository(),
        reservation_repo=DjangoStockReservationRepository(),
        movement_repo=DjangoStockMovementRepository(),
    )


# ===================== Admin/Staff API Views =====================

class AdminStockItemViewSet(viewsets.ViewSet):
    """ViewSet for admin stock item management."""
    
    permission_classes = [IsAdminOrStaff]
    
    def list(self, request: Request):
        """List stock items with filtering."""
        from ..infrastructure.models import StockItemModel
        from django_filters.rest_framework import DjangoFilterBackend
        
        # Get filters from query params
        product_id = request.query_params.get("product_id")
        warehouse_code = request.query_params.get("warehouse_code")
        is_active = request.query_params.get("is_active", "true").lower() == "true"
        
        queryset = StockItemModel.objects.filter(is_active=is_active)
        
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        if warehouse_code:
            queryset = queryset.filter(warehouse_code=warehouse_code)
        
        # Pagination
        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 20))
        start = (page - 1) * limit
        
        total = queryset.count()
        items = queryset[start:start + limit]
        
        serializer = StockItemSerializer(
            [
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "variant_id": item.variant_id,
                    "sku": item.sku,
                    "warehouse_code": item.warehouse_code,
                    "on_hand_quantity": item.on_hand_quantity,
                    "reserved_quantity": item.reserved_quantity,
                    "available_quantity": item.available_quantity,
                    "safety_stock": item.safety_stock,
                    "is_in_stock": item.is_in_stock(),
                    "is_low_stock": item.is_low_stock(),
                    "is_active": item.is_active,
                    "created_at": item.created_at,
                    "updated_at": item.updated_at,
                }
                for item in items
            ],
            many=True,
        )
        
        return success_response(
            message="Stock items retrieved",
            data={
                "total": total,
                "page": page,
                "limit": limit,
                "items": serializer.data,
            },
        )
    
    def create(self, request: Request):
        """Create a new stock item."""
        serializer = CreateStockItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            dto = CreateStockItemDTO(**serializer.validated_data)
            service = get_inventory_service()
            result = service.create_stock_item(dto)
            
            result_dict = {
                "id": result.id,
                "product_id": result.product_id,
                "variant_id": result.variant_id,
                "sku": result.sku,
                "warehouse_code": result.warehouse_code,
                "on_hand_quantity": result.on_hand_quantity,
                "reserved_quantity": result.reserved_quantity,
                "available_quantity": result.available_quantity,
                "safety_stock": result.safety_stock,
                "is_in_stock": result.is_in_stock,
                "is_low_stock": result.is_low_stock,
                "is_active": result.is_active,
                "created_at": result.created_at,
                "updated_at": result.updated_at,
            }
            
            return success_response(
                message="Stock item created successfully",
                data=result_dict,
                http_status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return error_response(
                message="Failed to create stock item",
                errors={"detail": str(e)},
                http_status=status.HTTP_400_BAD_REQUEST,
            )
    
    def retrieve(self, request: Request, pk=None):
        """Get a single stock item."""
        try:
            service = get_inventory_service()
            result = service.get_stock_item(UUID(pk))
            
            if not result:
                return error_response(
                    message="Stock item not found",
                    http_status=status.HTTP_404_NOT_FOUND,
                )
            
            result_dict = {
                "id": result.id,
                "product_id": result.product_id,
                "variant_id": result.variant_id,
                "sku": result.sku,
                "warehouse_code": result.warehouse_code,
                "on_hand_quantity": result.on_hand_quantity,
                "reserved_quantity": result.reserved_quantity,
                "available_quantity": result.available_quantity,
                "safety_stock": result.safety_stock,
                "is_in_stock": result.is_in_stock,
                "is_low_stock": result.is_low_stock,
                "is_active": result.is_active,
                "created_at": result.created_at,
                "updated_at": result.updated_at,
            }
            
            return success_response(
                message="Stock item retrieved",
                data=result_dict,
            )
        except ValueError as e:
            return error_response(
                message="Invalid stock item ID",
                errors={"detail": str(e)},
                http_status=status.HTTP_400_BAD_REQUEST,
            )
    
    def partial_update(self, request: Request, pk=None):
        """Update a stock item."""
        serializer = UpdateStockItemSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        try:
            service = get_inventory_service()
            dto = UpdateStockItemDTO(**serializer.validated_data)
            result = service.update_stock_item(UUID(pk), dto)
            
            result_dict = {
                "id": result.id,
                "product_id": result.product_id,
                "variant_id": result.variant_id,
                "sku": result.sku,
                "warehouse_code": result.warehouse_code,
                "on_hand_quantity": result.on_hand_quantity,
                "reserved_quantity": result.reserved_quantity,
                "available_quantity": result.available_quantity,
                "safety_stock": result.safety_stock,
                "is_in_stock": result.is_in_stock,
                "is_low_stock": result.is_low_stock,
                "is_active": result.is_active,
                "created_at": result.created_at,
                "updated_at": result.updated_at,
            }
            
            return success_response(
                message="Stock item updated",
                data=result_dict,
            )
        except ValueError as e:
            return error_response(
                message="Failed to update stock item",
                errors={"detail": str(e)},
                http_status=status.HTTP_400_BAD_REQUEST,
            )
    
    @action(detail=True, methods=["post"])
    def stock_in(self, request: Request, pk=None):
        """Process stock in."""
        serializer = StockInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            service = get_inventory_service()
            dto = StockInDTO(**serializer.validated_data)
            stock_dto, movement_dict = service.stock_in(UUID(pk), dto)
            
            stock_dict = {
                "id": stock_dto.id,
                "product_id": stock_dto.product_id,
                "available_quantity": stock_dto.available_quantity,
                "on_hand_quantity": stock_dto.on_hand_quantity,
            }
            
            return success_response(
                message="Stock in processed",
                data={
                    "stock_item": stock_dict,
                    "movement": movement_dict,
                },
            )
        except ValueError as e:
            return error_response(
                message="Failed to process stock in",
                errors={"detail": str(e)},
                http_status=status.HTTP_400_BAD_REQUEST,
            )
    
    @action(detail=True, methods=["post"])
    def stock_out(self, request: Request, pk=None):
        """Process stock out."""
        serializer = StockOutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            service = get_inventory_service()
            dto = StockOutDTO(**serializer.validated_data)
            stock_dto, movement_dict = service.stock_out(UUID(pk), dto)
            
            stock_dict = {
                "id": stock_dto.id,
                "product_id": stock_dto.product_id,
                "available_quantity": stock_dto.available_quantity,
                "on_hand_quantity": stock_dto.on_hand_quantity,
            }
            
            return success_response(
                message="Stock out processed",
                data={
                    "stock_item": stock_dict,
                    "movement": movement_dict,
                },
            )
        except ValueError as e:
            return error_response(
                message="Failed to process stock out",
                errors={"detail": str(e)},
                http_status=status.HTTP_400_BAD_REQUEST,
            )
    
    @action(detail=True, methods=["post"])
    def adjust(self, request: Request, pk=None):
        """Adjust stock level."""
        serializer = AdjustStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            service = get_inventory_service()
            dto = AdjustStockDTO(**serializer.validated_data)
            stock_dto, movement_dict = service.adjust_stock(UUID(pk), dto)
            
            stock_dict = {
                "id": stock_dto.id,
                "product_id": stock_dto.product_id,
                "available_quantity": stock_dto.available_quantity,
                "on_hand_quantity": stock_dto.on_hand_quantity,
            }
            
            return success_response(
                message="Stock adjusted",
                data={
                    "stock_item": stock_dict,
                    "movement": movement_dict,
                },
            )
        except ValueError as e:
            return error_response(
                message="Failed to adjust stock",
                errors={"detail": str(e)},
                http_status=status.HTTP_400_BAD_REQUEST,
            )
    
    @action(detail=True, methods=["get"])
    def movements(self, request: Request, pk=None):
        """Get movements for stock item."""
        try:
            service = get_inventory_service()
            movements = service.get_stock_movements(UUID(pk), limit=100)
            
            return success_response(
                message="Movements retrieved",
                data=movements,
            )
        except ValueError as e:
            return error_response(
                message="Failed to get movements",
                errors={"detail": str(e)},
                http_status=status.HTTP_400_BAD_REQUEST,
            )


# ===================== Internal API Views =====================

class InternalInventoryViewSet(viewsets.ViewSet):
    """ViewSet for internal service-to-service APIs."""
    
    permission_classes = [IsInternal]
    
    @action(detail=False, methods=["post"])
    def check_availability(self, request: Request):
        """Check availability for multiple items."""
        serializer = CheckAvailabilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            service = get_inventory_service()
            dtos = [
                CheckAvailabilityItemDTO(**item)
                for item in serializer.validated_data["items"]
            ]
            
            results = service.check_availability(dtos)
            
            result_list = [
                {
                    "product_id": r.product_id,
                    "variant_id": r.variant_id,
                    "requested_quantity": r.requested_quantity,
                    "available_quantity": r.available_quantity,
                    "can_reserve": r.can_reserve,
                    "is_in_stock": r.is_in_stock,
                    "stock_item_id": r.stock_item_id,
                }
                for r in results
            ]
            
            return success_response(
                message="Availability checked",
                data={"items": result_list},
            )
        except Exception as e:
            return error_response(
                message="Failed to check availability",
                errors={"detail": str(e)},
                http_status=status.HTTP_400_BAD_REQUEST,
            )
    
    @action(detail=False, methods=["post"])
    def reservations(self, request: Request):
        """Create a reservation."""
        serializer = CreateReservationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            service = get_inventory_service()
            dto = CreateReservationDTO(**serializer.validated_data)
            result = service.create_reservation(dto)
            
            return success_response(
                message="Reservation created",
                data=result,
                http_status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return error_response(
                message="Failed to create reservation",
                errors={"detail": str(e)},
                http_status=status.HTTP_400_BAD_REQUEST,
            )
    
    @action(detail=False, methods=["get"], url_path="products/(?P<product_id>[^/]+)/availability")
    def product_availability(self, request: Request, product_id=None):
        """Get product availability."""
        try:
            service = get_inventory_service()
            result = service.get_product_availability(product_id)
            
            result_dict = {
                "product_id": result.product_id,
                "total_on_hand": result.total_on_hand,
                "total_reserved": result.total_reserved,
                "total_available": result.total_available,
                "warehouses": result.warehouses,
            }
            
            return success_response(
                message="Product availability retrieved",
                data=result_dict,
            )
        except Exception as e:
            return error_response(
                message="Failed to get product availability",
                errors={"detail": str(e)},
                http_status=status.HTTP_400_BAD_REQUEST,
            )
    
    @action(detail=False, methods=["post"], url_path="reserve")
    def reserve(self, request: Request):
        """
        Bulk reserve stock for order items (called by order_service).
        
        Request payload:
        {
            "order_id": "uuid",
            "user_id": "uuid",
            "items": [
                {
                    "product_id": "uuid",
                    "variant_id": "uuid" (optional),
                    "quantity": 5
                },
                ...
            ]
        }
        
        ISSUE FIX #4: Uses STOCK_RESERVATION_TIMEOUT_MINUTES config for expiry.
        """
        try:
            service = get_inventory_service()
            order_id = request.data.get("order_id")
            user_id = request.data.get("user_id")
            items_data = request.data.get("items", [])
            
            reservation_ids = []
            
            for item in items_data:
                dto = CreateReservationDTO(
                    product_id=item.get("product_id"),
                    variant_id=item.get("variant_id"),
                    quantity=item.get("quantity", 1),
                    order_id=order_id,
                    user_id=user_id,
                    # expires_in_minutes will be set from config in DTO.__post_init__()
                )
                result = service.create_reservation(dto)
                reservation_ids.append(result.get("id"))
            
            return success_response(
                message="Reservations created",
                data={"reservation_ids": reservation_ids},
                http_status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return error_response(
                message="Failed to create reservations",
                errors={"detail": str(e)},
                http_status=status.HTTP_400_BAD_REQUEST,
            )
    
    @action(detail=False, methods=["post"], url_path="confirm")
    def confirm(self, request: Request):
        """
        Confirm stock reservations after payment success (called by order_service).
        
        Request payload:
        {
            "order_id": "uuid",
            "reservation_ids": ["id1", "id2", ...]
        }
        """
        try:
            service = get_inventory_service()
            reservation_ids = request.data.get("reservation_ids", [])
            
            confirmed_count = 0
            for res_id in reservation_ids:
                try:
                    service.confirm_reservation(UUID(res_id))
                    confirmed_count += 1
                except Exception as e:
                    # ISSUE FIX #2: Log but continue processing other reservations
                    logger.error(f"Failed to confirm reservation {res_id}: {e}")
            
            return success_response(
                message=f"Reservations confirmed ({confirmed_count}/{len(reservation_ids)})",
                data={"confirmed_count": confirmed_count, "total": len(reservation_ids)},
            )
        except Exception as e:
            return error_response(
                message="Failed to confirm reservations",
                errors={"detail": str(e)},
                http_status=status.HTTP_400_BAD_REQUEST,
            )
    
    @action(detail=False, methods=["post"], url_path="release")
    def release(self, request: Request):
        """
        Release stock reservations (on payment failure, order cancel, expiry, etc).
        
        Request payload:
        {
            "order_id": "uuid",
            "reservation_ids": ["id1", "id2", ...],
            "reason": "Order cancelled"
        }
        """
        try:
            service = get_inventory_service()
            reservation_ids = request.data.get("reservation_ids", [])
            reason = request.data.get("reason", "manual_release")
            
            released_count = 0
            for res_id in reservation_ids:
                try:
                    service.release_reservation(UUID(res_id), reason)
                    released_count += 1
                except Exception as e:
                    logger.error(f"Failed to release reservation {res_id}: {e}")
            
            return success_response(
                message=f"Reservations released ({released_count}/{len(reservation_ids)})",
                data={"released_count": released_count, "total": len(reservation_ids)},
            )
        except Exception as e:
            return error_response(
                message="Failed to release reservations",
                errors={"detail": str(e)},
                http_status=status.HTTP_400_BAD_REQUEST,
            )
