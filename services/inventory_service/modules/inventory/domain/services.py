"""
Domain services for Inventory context.

Contains business logic that doesn't naturally fit into a single entity.
"""
from typing import List, Optional
from datetime import datetime

from .entities import StockItem, StockReservation, StockMovement
from .enums import StockMovementType


class InventoryDomainService:
    """
    Domain service for inventory operations.
    
    Orchestrates complex business processes involving multiple entities.
    """
    
    @staticmethod
    def process_stock_in(
        stock_item: StockItem,
        quantity: int,
        reference_id: Optional[str] = None,
        note: Optional[str] = None,
    ) -> StockMovement:
        """
        Process incoming stock.
        
        Creates stock movement record and updates stock item.
        """
        stock_item.receive_stock(quantity, reason="stock_in")
        
        movement = StockMovement(
            id=None,
            stock_item_id=stock_item.id,
            product_reference=stock_item.product_reference,
            movement_type=StockMovementType.STOCK_IN,
            quantity=quantity,
            reference_type="purchase_order",
            reference_id=reference_id,
            note=note,
        )
        
        return movement
    
    @staticmethod
    def process_stock_out(
        stock_item: StockItem,
        quantity: int,
        reference_id: Optional[str] = None,
        note: Optional[str] = None,
    ) -> StockMovement:
        """
        Process outgoing stock (without reservation).
        
        Used for direct stock out operations.
        """
        if stock_item.on_hand_quantity < quantity:
            raise ValueError(
                f"Insufficient stock. On-hand: {stock_item.on_hand_quantity}, "
                f"Requested: {quantity}"
            )
        
        stock_item.adjust_stock(-quantity, reason="stock_out")
        
        movement = StockMovement(
            id=None,
            stock_item_id=stock_item.id,
            product_reference=stock_item.product_reference,
            movement_type=StockMovementType.STOCK_OUT,
            quantity=quantity,
            reference_type="manual_stock_out",
            reference_id=reference_id,
            note=note,
        )
        
        return movement
    
    @staticmethod
    def adjust_stock(
        stock_item: StockItem,
        adjustment: int,
        adjustment_type: str = "adjustment_increase",
        reason: str = "manual_adjustment",
        note: Optional[str] = None,
    ) -> StockMovement:
        """
        Adjust stock level (increase or decrease).
        
        Used for inventory corrections and adjustments.
        """
        stock_item.adjust_stock(adjustment, reason=reason)
        
        movement_type = (
            StockMovementType.ADJUSTMENT_INCREASE
            if adjustment > 0
            else StockMovementType.ADJUSTMENT_DECREASE
        )
        
        movement = StockMovement(
            id=None,
            stock_item_id=stock_item.id,
            product_reference=stock_item.product_reference,
            movement_type=movement_type,
            quantity=abs(adjustment),
            reference_type="manual_adjustment",
            note=note or reason,
        )
        
        return movement
    
    @staticmethod
    def confirm_reservation_and_deduct(
        stock_item: StockItem,
        reservation: StockReservation,
    ) -> List[StockMovement]:
        """
        Confirm a reservation and deduct from on-hand stock.
        
        This is called when payment is confirmed or order is finalized.
        Returns both the confirmation and deduction movements.
        """
        if not reservation.can_confirm():
            raise ValueError(
                f"Cannot confirm reservation {reservation.id}. "
                f"Status: {reservation.status}"
            )
        
        # Confirm in stock item
        stock_item.confirm_reservation(reservation.quantity)
        reservation.confirm()
        
        # Create movement records
        movements = []
        
        # Record the confirmation
        movements.append(
            StockMovement(
                id=None,
                stock_item_id=stock_item.id,
                product_reference=stock_item.product_reference,
                movement_type=StockMovementType.RESERVATION_CONFIRMED,
                quantity=reservation.quantity,
                reference_type="order",
                reference_id=reservation.order_id,
                note=f"Reservation {reservation.id} confirmed",
            )
        )
        
        # Record the deduction
        movements.append(
            StockMovement(
                id=None,
                stock_item_id=stock_item.id,
                product_reference=stock_item.product_reference,
                movement_type=StockMovementType.STOCK_OUT,
                quantity=reservation.quantity,
                reference_type="order",
                reference_id=reservation.order_id,
                note=f"Order {reservation.order_id} stock confirmed",
            )
        )
        
        return movements
    
    @staticmethod
    def release_reservation_stock(
        stock_item: StockItem,
        reservation: StockReservation,
        reason: str = "manual_release",
    ) -> StockMovement:
        """
        Release a reservation and return stock to available.
        
        Called when order is cancelled, payment fails, or reservation expires.
        """
        if not reservation.can_release():
            raise ValueError(
                f"Cannot release reservation {reservation.id}. "
                f"Status: {reservation.status}"
            )
        
        stock_item.release_reservation(reservation.quantity)
        reservation.release()
        
        movement = StockMovement(
            id=None,
            stock_item_id=stock_item.id,
            product_reference=stock_item.product_reference,
            movement_type=StockMovementType.RESERVATION_RELEASED,
            quantity=reservation.quantity,
            reference_type="order",
            reference_id=reservation.order_id,
            note=f"Reservation {reservation.id} released: {reason}",
        )
        
        return movement
