"""
Repository implementations for Inventory domain.

Adapts Django ORM to work with domain repositories.
"""
from typing import List, Optional
from uuid import UUID

from ..domain.entities import StockItem, StockReservation, StockMovement
from ..domain.value_objects import ProductReference
from ..domain.repositories import (
    StockItemRepository,
    StockReservationRepository,
    StockMovementRepository,
)
from .models import StockItemModel, StockReservationModel, StockMovementModel


class DjangoStockItemRepository(StockItemRepository):
    """Django ORM implementation of StockItemRepository."""
    
    def save(self, stock_item: StockItem) -> StockItem:
        """Save stock item to database."""
        model, _ = StockItemModel.objects.get_or_create(
            id=stock_item.id,
            defaults={
                "product_id": stock_item.product_id,
                "variant_id": stock_item.variant_id,
                "sku": stock_item.sku,
                "warehouse_code": stock_item.warehouse_code,
                "on_hand_quantity": stock_item.on_hand_quantity,
                "reserved_quantity": stock_item.reserved_quantity,
                "safety_stock": stock_item.safety_stock,
                "is_active": stock_item.is_active,
            },
        )
        
        # Update if exists
        model.on_hand_quantity = stock_item.on_hand_quantity
        model.reserved_quantity = stock_item.reserved_quantity
        model.safety_stock = stock_item.safety_stock
        model.is_active = stock_item.is_active
        model.save(update_fields=[
            "on_hand_quantity",
            "reserved_quantity",
            "safety_stock",
            "is_active",
            "updated_at",
        ])
        
        return self._model_to_entity(model)
    
    def get_by_id(self, id: UUID) -> Optional[StockItem]:
        """Get stock item by ID."""
        try:
            model = StockItemModel.objects.get(id=id)
            return self._model_to_entity(model)
        except StockItemModel.DoesNotExist:
            return None
    
    def get_by_product_and_warehouse(
        self,
        product_id: str,
        warehouse_code: str,
        variant_id: Optional[str] = None,
    ) -> Optional[StockItem]:
        """Get stock item by product, variant, and warehouse."""
        try:
            model = StockItemModel.objects.get(
                product_id=product_id,
                variant_id=variant_id,
                warehouse_code=warehouse_code,
                is_active=True,
            )
            return self._model_to_entity(model)
        except StockItemModel.DoesNotExist:
            return None
    
    def get_by_product(self, product_id: str) -> List[StockItem]:
        """Get all stock items for a product."""
        models = StockItemModel.objects.filter(
            product_id=product_id,
            is_active=True,
        )
        return [self._model_to_entity(m) for m in models]
    
    def get_by_variant(self, variant_id: str) -> List[StockItem]:
        """Get all stock items for a variant."""
        models = StockItemModel.objects.filter(
            variant_id=variant_id,
            is_active=True,
        )
        return [self._model_to_entity(m) for m in models]
    
    def get_by_warehouse(self, warehouse_code: str) -> List[StockItem]:
        """Get all stock items in a warehouse."""
        models = StockItemModel.objects.filter(
            warehouse_code=warehouse_code,
            is_active=True,
        )
        return [self._model_to_entity(m) for m in models]
    
    def get_low_stock_items(self, warehouse_code: Optional[str] = None) -> List[StockItem]:
        """Get items with on_hand <= safety_stock."""
        from django.db.models import F
        query = StockItemModel.objects.filter(
            is_active=True,
            on_hand_quantity__lte=F("safety_stock"),
        )
        if warehouse_code:
            query = query.filter(warehouse_code=warehouse_code)
        
        return [self._model_to_entity(m) for m in query]
    
    def delete(self, id: UUID) -> bool:
        """Soft delete a stock item."""
        model = StockItemModel.objects.get(id=id)
        model.is_active = False
        model.save(update_fields=["is_active", "updated_at"])
        return True
    
    @staticmethod
    def _model_to_entity(model: StockItemModel) -> StockItem:
        """Convert Django model to domain entity."""
        return StockItem(
            id=model.id,
            product_reference=ProductReference(
                product_id=str(model.product_id),
                variant_id=str(model.variant_id) if model.variant_id else None,
                sku=model.sku,
            ),
            warehouse_code=model.warehouse_code,
            on_hand_quantity=model.on_hand_quantity,
            reserved_quantity=model.reserved_quantity,
            safety_stock=model.safety_stock,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class DjangoStockReservationRepository(StockReservationRepository):
    """Django ORM implementation of StockReservationRepository."""
    
    def save(self, reservation: StockReservation) -> StockReservation:
        """Save reservation to database."""
        model, created = StockReservationModel.objects.get_or_create(
            id=reservation.id,
            defaults={
                "reservation_code": self._generate_reservation_code(reservation),
                "stock_item_id": reservation.stock_item_id,
                "product_id": reservation.product_id,
                "variant_id": reservation.variant_id,
                "order_id": reservation.order_id,
                "cart_id": reservation.cart_id,
                "user_id": reservation.user_id,
                "quantity": reservation.quantity,
                "status": reservation.status.value,
                "expires_at": reservation.expires_at,
                "metadata": reservation.metadata,
            },
        )
        
        # Update if exists
        if not created:
            model.status = reservation.status.value
            model.expires_at = reservation.expires_at
            model.metadata = reservation.metadata
            model.save(update_fields=["status", "expires_at", "metadata", "updated_at"])
        
        return self._model_to_entity(model)
    
    def get_by_id(self, id: UUID) -> Optional[StockReservation]:
        """Get reservation by ID."""
        try:
            model = StockReservationModel.objects.get(id=id)
            return self._model_to_entity(model)
        except StockReservationModel.DoesNotExist:
            return None
    
    def get_by_order(self, order_id: str) -> List[StockReservation]:
        """Get all reservations for an order."""
        models = StockReservationModel.objects.filter(order_id=order_id)
        return [self._model_to_entity(m) for m in models]
    
    def get_by_cart(self, cart_id: str) -> List[StockReservation]:
        """Get all reservations for a cart."""
        models = StockReservationModel.objects.filter(cart_id=cart_id)
        return [self._model_to_entity(m) for m in models]
    
    def get_by_product(self, product_id: str) -> List[StockReservation]:
        """Get all reservations for a product."""
        models = StockReservationModel.objects.filter(product_id=product_id)
        return [self._model_to_entity(m) for m in models]
    
    def get_by_stock_item(self, stock_item_id: UUID) -> List[StockReservation]:
        """Get all reservations for a stock item."""
        models = StockReservationModel.objects.filter(stock_item_id=stock_item_id)
        return [self._model_to_entity(m) for m in models]
    
    def get_active_reservations(self, stock_item_id: UUID) -> List[StockReservation]:
        """Get active reservations for a stock item."""
        from django.utils import timezone
        models = StockReservationModel.objects.filter(
            stock_item_id=stock_item_id,
            status="active",
            expires_at__gt=timezone.now(),
        )
        return [self._model_to_entity(m) for m in models]
    
    def get_expired_reservations(self) -> List[StockReservation]:
        """Get expired reservations."""
        from django.utils import timezone
        models = StockReservationModel.objects.filter(
            status="active",
            expires_at__lte=timezone.now(),
        )
        return [self._model_to_entity(m) for m in models]
    
    def delete(self, id: UUID) -> bool:
        """Delete a reservation."""
        StockReservationModel.objects.filter(id=id).delete()
        return True
    
    @staticmethod
    def _model_to_entity(model: StockReservationModel) -> StockReservation:
        """Convert Django model to domain entity."""
        from ..domain.enums import ReservationStatus
        
        return StockReservation(
            id=model.id,
            stock_item_id=model.stock_item_id,
            product_reference=ProductReference(
                product_id=str(model.product_id),
                variant_id=str(model.variant_id) if model.variant_id else None,
            ),
            quantity=model.quantity,
            status=ReservationStatus(model.status),
            order_id=str(model.order_id) if model.order_id else None,
            cart_id=str(model.cart_id) if model.cart_id else None,
            user_id=str(model.user_id) if model.user_id else None,
            expires_at=model.expires_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
            metadata=model.metadata,
        )
    
    @staticmethod
    def _generate_reservation_code(reservation: StockReservation) -> str:
        """Generate unique reservation code."""
        import shortuuid
        return f"RES-{shortuuid.ShortUUID().random(12).upper()}"


class DjangoStockMovementRepository(StockMovementRepository):
    """Django ORM implementation of StockMovementRepository."""
    
    def save(self, movement: StockMovement) -> StockMovement:
        """Save movement to database (immutable)."""
        model = StockMovementModel.objects.create(
            stock_item_id=movement.stock_item_id,
            product_id=movement.product_id,
            variant_id=movement.variant_id,
            movement_type=movement.movement_type.value,
            quantity=movement.quantity,
            reference_type=movement.reference_type,
            reference_id=movement.reference_id,
            note=movement.note,
            created_by=movement.created_by,
            metadata=movement.metadata,
        )
        return self._model_to_entity(model)
    
    def get_by_id(self, id: UUID) -> Optional[StockMovement]:
        """Get movement by ID."""
        try:
            model = StockMovementModel.objects.get(id=id)
            return self._model_to_entity(model)
        except StockMovementModel.DoesNotExist:
            return None
    
    def get_by_stock_item(self, stock_item_id: UUID, limit: int = 100) -> List[StockMovement]:
        """Get movements for a stock item."""
        models = StockMovementModel.objects.filter(
            stock_item_id=stock_item_id,
        ).order_by("-created_at")[:limit]
        return [self._model_to_entity(m) for m in models]
    
    def get_by_product(self, product_id: str, limit: int = 100) -> List[StockMovement]:
        """Get movements for a product."""
        models = StockMovementModel.objects.filter(
            product_id=product_id,
        ).order_by("-created_at")[:limit]
        return [self._model_to_entity(m) for m in models]
    
    def get_by_reference(self, reference_type: str, reference_id: str) -> List[StockMovement]:
        """Get movements by reference."""
        models = StockMovementModel.objects.filter(
            reference_type=reference_type,
            reference_id=reference_id,
        ).order_by("-created_at")
        return [self._model_to_entity(m) for m in models]
    
    @staticmethod
    def _model_to_entity(model: StockMovementModel) -> StockMovement:
        """Convert Django model to domain entity."""
        from ..domain.enums import StockMovementType
        
        return StockMovement(
            id=model.id,
            stock_item_id=model.stock_item_id,
            product_reference=ProductReference(
                product_id=str(model.product_id),
                variant_id=str(model.variant_id) if model.variant_id else None,
            ),
            movement_type=StockMovementType(model.movement_type),
            quantity=model.quantity,
            reference_type=model.reference_type,
            reference_id=model.reference_id,
            note=model.note,
            created_by=str(model.created_by) if model.created_by else None,
            created_at=model.created_at,
            metadata=model.metadata,
        )
