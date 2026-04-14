"""
Application services for Inventory context.

Implements use cases and orchestrates domain services and repositories.
"""
from typing import List, Optional
from uuid import uuid4, UUID
from datetime import datetime, timedelta

from ..domain.entities import StockItem, StockReservation, StockMovement
from ..domain.value_objects import ProductReference
from ..domain.enums import StockMovementType
from ..domain.services import InventoryDomainService
from ..domain.repositories import (
    StockItemRepository,
    StockReservationRepository,
    StockMovementRepository,
)
from .dtos import (
    StockItemDTO,
    CreateStockItemDTO,
    UpdateStockItemDTO,
    StockInDTO,
    StockOutDTO,
    AdjustStockDTO,
    CreateReservationDTO,
    AvailabilityResultDTO,
    CheckAvailabilityItemDTO,
    InventorySummaryDTO,
)


class InventoryApplicationService:
    """
    Application service for inventory operations.
    
    Orchestrates domain services and repositories to implement use cases.
    """
    
    def __init__(
        self,
        stock_item_repo: StockItemRepository,
        reservation_repo: StockReservationRepository,
        movement_repo: StockMovementRepository,
    ):
        self.stock_item_repo = stock_item_repo
        self.reservation_repo = reservation_repo
        self.movement_repo = movement_repo
        self.domain_service = InventoryDomainService()
    
    # ===================== Stock Item Operations =====================
    
    def create_stock_item(self, dto: CreateStockItemDTO) -> StockItemDTO:
        """Create a new stock item."""
        # Check for existing
        existing = self.stock_item_repo.get_by_product_and_warehouse(
            product_id=dto.product_id,
            warehouse_code=dto.warehouse_code,
            variant_id=dto.variant_id,
        )
        
        if existing:
            raise ValueError(
                f"Stock item already exists for "
                f"product={dto.product_id}, variant={dto.variant_id}, "
                f"warehouse={dto.warehouse_code}"
            )
        
        # Create entity
        stock_item = StockItem(
            id=uuid4(),
            product_reference=ProductReference(
                product_id=dto.product_id,
                variant_id=dto.variant_id,
                sku=dto.sku,
            ),
            warehouse_code=dto.warehouse_code,
            on_hand_quantity=dto.on_hand_quantity,
            safety_stock=dto.safety_stock,
        )
        
        # Save
        saved = self.stock_item_repo.save(stock_item)
        
        return self._stock_item_to_dto(saved)
    
    def get_stock_item(self, stock_item_id: UUID) -> Optional[StockItemDTO]:
        """Get stock item by ID."""
        stock_item = self.stock_item_repo.get_by_id(stock_item_id)
        return self._stock_item_to_dto(stock_item) if stock_item else None
    
    def update_stock_item(
        self,
        stock_item_id: UUID,
        dto: UpdateStockItemDTO,
    ) -> StockItemDTO:
        """Update stock item properties."""
        stock_item = self.stock_item_repo.get_by_id(stock_item_id)
        if not stock_item:
            raise ValueError(f"Stock item {stock_item_id} not found")
        
        if dto.safety_stock is not None:
            stock_item.safety_stock = dto.safety_stock
        
        if dto.is_active is not None:
            if dto.is_active:
                stock_item.activate()
            else:
                stock_item.deactivate()
        
        saved = self.stock_item_repo.save(stock_item)
        return self._stock_item_to_dto(saved)
    
    def get_product_stock_items(self, product_id: str) -> List[StockItemDTO]:
        """Get all stock items for a product."""
        items = self.stock_item_repo.get_by_product(product_id)
        return [self._stock_item_to_dto(item) for item in items]
    
    def get_variant_stock_items(self, variant_id: str) -> List[StockItemDTO]:
        """Get all stock items for a variant."""
        items = self.stock_item_repo.get_by_variant(variant_id)
        return [self._stock_item_to_dto(item) for item in items]
    
    # ===================== Stock Operations =====================
    
    def stock_in(self, stock_item_id: UUID, dto: StockInDTO) -> tuple[StockItemDTO, any]:
        """Process stock in (receive)."""
        stock_item = self.stock_item_repo.get_by_id(stock_item_id)
        if not stock_item:
            raise ValueError(f"Stock item {stock_item_id} not found")
        
        # Process through domain service
        movement = self.domain_service.process_stock_in(
            stock_item,
            quantity=dto.quantity,
            reference_id=dto.reference_id,
            note=dto.note,
        )
        
        # Persist
        self.stock_item_repo.save(stock_item)
        self.movement_repo.save(movement)
        
        return self._stock_item_to_dto(stock_item), self._movement_to_dict(movement)
    
    def stock_out(self, stock_item_id: UUID, dto: StockOutDTO) -> tuple[StockItemDTO, any]:
        """Process stock out (direct removal)."""
        stock_item = self.stock_item_repo.get_by_id(stock_item_id)
        if not stock_item:
            raise ValueError(f"Stock item {stock_item_id} not found")
        
        # Process through domain service
        movement = self.domain_service.process_stock_out(
            stock_item,
            quantity=dto.quantity,
            reference_id=dto.reference_id,
            note=dto.note,
        )
        
        # Persist
        self.stock_item_repo.save(stock_item)
        self.movement_repo.save(movement)
        
        return self._stock_item_to_dto(stock_item), self._movement_to_dict(movement)
    
    def adjust_stock(self, stock_item_id: UUID, dto: AdjustStockDTO) -> tuple[StockItemDTO, any]:
        """Adjust stock level (positive or negative)."""
        stock_item = self.stock_item_repo.get_by_id(stock_item_id)
        if not stock_item:
            raise ValueError(f"Stock item {stock_item_id} not found")
        
        adjustment_type = (
            "adjustment_increase" if dto.quantity > 0 else "adjustment_decrease"
        )
        
        movement = self.domain_service.adjust_stock(
            stock_item,
            adjustment=dto.quantity,
            adjustment_type=adjustment_type,
            reason=dto.reason,
        )
        
        # Persist
        self.stock_item_repo.save(stock_item)
        self.movement_repo.save(movement)
        
        return self._stock_item_to_dto(stock_item), self._movement_to_dict(movement)
    
    def get_stock_movements(self, stock_item_id: UUID, limit: int = 100) -> List[dict]:
        """Get recent stock movements for an item."""
        movements = self.movement_repo.get_by_stock_item(stock_item_id, limit=limit)
        return [self._movement_to_dict(m) for m in movements]
    
    # ===================== Reservation Operations =====================
    
    def create_reservation(self, dto: CreateReservationDTO) -> dict:
        """Create a stock reservation."""
        # Get or create stock item
        stock_item = self.stock_item_repo.get_by_product_and_warehouse(
            product_id=dto.product_id,
            warehouse_code="MAIN",  # Default warehouse
            variant_id=dto.variant_id,
        )
        
        if not stock_item:
            raise ValueError(
                f"No stock found for product={dto.product_id}, "
                f"variant={dto.variant_id}"
            )
        
        if not stock_item.can_reserve(dto.quantity):
            raise ValueError(
                f"Insufficient stock. Available: {stock_item.available_quantity}, "
                f"Requested: {dto.quantity}"
            )
        
        # Create reservation through domain
        reservation = stock_item.create_reservation(dto.quantity)
        
        # Set optional fields
        reservation.order_id = dto.order_id
        reservation.cart_id = dto.cart_id
        reservation.user_id = dto.user_id
        reservation.expires_at = datetime.utcnow() + timedelta(
            minutes=dto.expires_in_minutes
        )
        
        # Persist
        self.stock_item_repo.save(stock_item)
        saved_reservation = self.reservation_repo.save(reservation)
        
        # Create movement record
        movement = StockMovement(
            id=uuid4(),
            stock_item_id=stock_item.id,
            product_reference=stock_item.product_reference,
            movement_type=StockMovementType.RESERVATION_CREATED,
            quantity=dto.quantity,
            reference_id=str(saved_reservation.id),
            note=f"Reservation created: {saved_reservation.id}",
        )
        self.movement_repo.save(movement)
        
        return self._reservation_to_dict(saved_reservation)
    
    def get_reservation(self, reservation_id: UUID) -> Optional[dict]:
        """Get reservation by ID."""
        reservation = self.reservation_repo.get_by_id(reservation_id)
        return self._reservation_to_dict(reservation) if reservation else None
    
    def confirm_reservation(self, reservation_id: UUID) -> dict:
        """Confirm a reservation (deduct from on-hand)."""
        reservation = self.reservation_repo.get_by_id(reservation_id)
        if not reservation:
            raise ValueError(f"Reservation {reservation_id} not found")
        
        stock_item = self.stock_item_repo.get_by_id(reservation.stock_item_id)
        if not stock_item:
            raise ValueError(f"Stock item for reservation not found")
        
        # Confirm through domain service
        movements = self.domain_service.confirm_reservation_and_deduct(
            stock_item, reservation
        )
        
        # Persist
        self.stock_item_repo.save(stock_item)
        self.reservation_repo.save(reservation)
        for movement in movements:
            self.movement_repo.save(movement)
        
        return self._reservation_to_dict(reservation)
    
    def release_reservation(
        self,
        reservation_id: UUID,
        reason: str = "manual_release",
    ) -> dict:
        """Release a reservation."""
        reservation = self.reservation_repo.get_by_id(reservation_id)
        if not reservation:
            raise ValueError(f"Reservation {reservation_id} not found")
        
        stock_item = self.stock_item_repo.get_by_id(reservation.stock_item_id)
        if not stock_item:
            raise ValueError(f"Stock item for reservation not found")
        
        # Release through domain service
        movement = self.domain_service.release_reservation_stock(
            stock_item, reservation, reason
        )
        
        # Persist
        self.stock_item_repo.save(stock_item)
        self.reservation_repo.save(reservation)
        self.movement_repo.save(movement)
        
        return self._reservation_to_dict(reservation)
    
    def cancel_reservation(self, reservation_id: UUID) -> dict:
        """Cancel a reservation."""
        return self.release_reservation(reservation_id, reason="cancelled")
    
    def get_product_reservations(self, product_id: str) -> List[dict]:
        """Get all reservations for a product."""
        reservations = self.reservation_repo.get_by_product(product_id)
        return [self._reservation_to_dict(r) for r in reservations]
    
    def get_order_reservations(self, order_id: str) -> List[dict]:
        """Get all reservations for an order."""
        reservations = self.reservation_repo.get_by_order(order_id)
        return [self._reservation_to_dict(r) for r in reservations]
    
    def expire_expired_reservations(self) -> List[dict]:
        """Find and expire all expired reservations."""
        expired = self.reservation_repo.get_expired_reservations()
        
        results = []
        for reservation in expired:
            if reservation.status.value == "active":
                stock_item = self.stock_item_repo.get_by_id(reservation.stock_item_id)
                if stock_item:
                    # Release the reservation
                    movement = self.domain_service.release_reservation_stock(
                        stock_item, reservation, reason="expired"
                    )
                    reservation.expire()
                    
                    # Persist
                    self.stock_item_repo.save(stock_item)
                    self.reservation_repo.save(reservation)
                    self.movement_repo.save(movement)
                    
                    results.append(self._reservation_to_dict(reservation))
        
        return results
    
    # ===================== Availability Check =====================
    
    def check_availability(self, items: List[CheckAvailabilityItemDTO]) -> List[AvailabilityResultDTO]:
        """Check availability for multiple items."""
        results = []
        
        for item_dto in items:
            stock_item = self.stock_item_repo.get_by_product_and_warehouse(
                product_id=item_dto.product_id,
                warehouse_code="MAIN",
                variant_id=item_dto.variant_id,
            )
            
            if not stock_item:
                result = AvailabilityResultDTO(
                    product_id=item_dto.product_id,
                    variant_id=item_dto.variant_id,
                    requested_quantity=item_dto.quantity,
                    available_quantity=0,
                    can_reserve=False,
                    is_in_stock=False,
                )
            else:
                can_reserve = stock_item.can_reserve(item_dto.quantity)
                result = AvailabilityResultDTO(
                    product_id=item_dto.product_id,
                    variant_id=item_dto.variant_id,
                    requested_quantity=item_dto.quantity,
                    available_quantity=stock_item.available_quantity,
                    can_reserve=can_reserve,
                    is_in_stock=stock_item.is_in_stock(),
                    stock_item_id=str(stock_item.id),
                )
            
            results.append(result)
        
        return results
    
    def get_product_availability(self, product_id: str) -> InventorySummaryDTO:
        """Get inventory summary for a product."""
        stock_items = self.stock_item_repo.get_by_product(product_id)
        
        total_on_hand = sum(s.on_hand_quantity for s in stock_items)
        total_reserved = sum(s.reserved_quantity for s in stock_items)
        total_available = sum(s.available_quantity for s in stock_items)
        
        warehouses = [
            {
                "warehouse_code": s.warehouse_code,
                "on_hand": s.on_hand_quantity,
                "reserved": s.reserved_quantity,
                "available": s.available_quantity,
            }
            for s in stock_items
        ]
        
        return InventorySummaryDTO(
            product_id=product_id,
            variant_id=None,
            total_on_hand=total_on_hand,
            total_reserved=total_reserved,
            total_available=total_available,
            warehouses=warehouses,
        )
    
    def get_variant_availability(self, variant_id: str) -> InventorySummaryDTO:
        """Get inventory summary for a variant."""
        stock_items = self.stock_item_repo.get_by_variant(variant_id)
        
        # Get product_id from first item
        product_id = stock_items[0].product_id if stock_items else None
        
        total_on_hand = sum(s.on_hand_quantity for s in stock_items)
        total_reserved = sum(s.reserved_quantity for s in stock_items)
        total_available = sum(s.available_quantity for s in stock_items)
        
        warehouses = [
            {
                "warehouse_code": s.warehouse_code,
                "on_hand": s.on_hand_quantity,
                "reserved": s.reserved_quantity,
                "available": s.available_quantity,
            }
            for s in stock_items
        ]
        
        return InventorySummaryDTO(
            product_id=product_id or "",
            variant_id=variant_id,
            total_on_hand=total_on_hand,
            total_reserved=total_reserved,
            total_available=total_available,
            warehouses=warehouses,
        )
    
    # ===================== Helper Methods =====================
    
    @staticmethod
    def _stock_item_to_dto(stock_item: StockItem) -> StockItemDTO:
        """Convert domain entity to DTO."""
        return StockItemDTO(
            id=str(stock_item.id),
            product_id=str(stock_item.product_id),
            variant_id=str(stock_item.variant_id) if stock_item.variant_id else None,
            sku=stock_item.sku,
            warehouse_code=stock_item.warehouse_code,
            on_hand_quantity=stock_item.on_hand_quantity,
            reserved_quantity=stock_item.reserved_quantity,
            available_quantity=stock_item.available_quantity,
            safety_stock=stock_item.safety_stock,
            is_in_stock=stock_item.is_in_stock(),
            is_low_stock=stock_item.is_low_stock(),
            is_active=stock_item.is_active,
            created_at=stock_item.created_at.isoformat(),
            updated_at=stock_item.updated_at.isoformat(),
        )
    
    @staticmethod
    def _movement_to_dict(movement: StockMovement) -> dict:
        """Convert movement entity to dict."""
        return {
            "id": str(movement.id),
            "stock_item_id": str(movement.stock_item_id),
            "product_id": str(movement.product_id),
            "variant_id": str(movement.variant_id) if movement.variant_id else None,
            "movement_type": movement.movement_type.value,
            "quantity": movement.quantity,
            "reference_type": movement.reference_type,
            "reference_id": movement.reference_id,
            "note": movement.note,
            "created_at": movement.created_at.isoformat(),
        }
    
    @staticmethod
    def _reservation_to_dict(reservation: StockReservation) -> dict:
        """Convert reservation entity to dict."""
        return {
            "id": str(reservation.id),
            "product_id": str(reservation.product_id),
            "variant_id": str(reservation.variant_id) if reservation.variant_id else None,
            "quantity": reservation.quantity,
            "status": reservation.status.value,
            "order_id": str(reservation.order_id) if reservation.order_id else None,
            "cart_id": str(reservation.cart_id) if reservation.cart_id else None,
            "user_id": str(reservation.user_id) if reservation.user_id else None,
            "expires_at": reservation.expires_at.isoformat(),
            "created_at": reservation.created_at.isoformat(),
            "updated_at": reservation.updated_at.isoformat(),
        }
