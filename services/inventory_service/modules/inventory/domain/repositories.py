"""
Repository interfaces for Inventory domain.

Defines contracts that infrastructure must implement.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from .entities import StockItem, StockReservation, StockMovement


class StockItemRepository(ABC):
    """Repository interface for StockItem entity."""
    
    @abstractmethod
    def save(self, stock_item: StockItem) -> StockItem:
        """Save or update a stock item."""
        pass
    
    @abstractmethod
    def get_by_id(self, id: UUID) -> Optional[StockItem]:
        """Retrieve stock item by ID."""
        pass
    
    @abstractmethod
    def get_by_product_and_warehouse(
        self,
        product_id: str,
        warehouse_code: str,
        variant_id: Optional[str] = None,
    ) -> Optional[StockItem]:
        """Retrieve stock item by product, variant, and warehouse."""
        pass
    
    @abstractmethod
    def get_by_product(self, product_id: str) -> List[StockItem]:
        """Retrieve all stock items for a product."""
        pass
    
    @abstractmethod
    def get_by_variant(self, variant_id: str) -> List[StockItem]:
        """Retrieve all stock items for a variant."""
        pass
    
    @abstractmethod
    def get_by_warehouse(self, warehouse_code: str) -> List[StockItem]:
        """Retrieve all stock items in a warehouse."""
        pass
    
    @abstractmethod
    def get_low_stock_items(self, warehouse_code: Optional[str] = None) -> List[StockItem]:
        """Retrieve items with quantity <= safety_stock."""
        pass
    
    @abstractmethod
    def delete(self, id: UUID) -> bool:
        """Delete a stock item."""
        pass


class StockReservationRepository(ABC):
    """Repository interface for StockReservation entity."""
    
    @abstractmethod
    def save(self, reservation: StockReservation) -> StockReservation:
        """Save or update a reservation."""
        pass
    
    @abstractmethod
    def get_by_id(self, id: UUID) -> Optional[StockReservation]:
        """Retrieve reservation by ID."""
        pass
    
    @abstractmethod
    def get_by_order(self, order_id: str) -> List[StockReservation]:
        """Retrieve all reservations for an order."""
        pass
    
    @abstractmethod
    def get_by_cart(self, cart_id: str) -> List[StockReservation]:
        """Retrieve all reservations for a cart."""
        pass
    
    @abstractmethod
    def get_by_product(self, product_id: str) -> List[StockReservation]:
        """Retrieve all reservations for a product."""
        pass
    
    @abstractmethod
    def get_by_stock_item(self, stock_item_id: UUID) -> List[StockReservation]:
        """Retrieve all reservations for a stock item."""
        pass
    
    @abstractmethod
    def get_active_reservations(self, stock_item_id: UUID) -> List[StockReservation]:
        """Retrieve active (non-expired) reservations for a stock item."""
        pass
    
    @abstractmethod
    def get_expired_reservations(self) -> List[StockReservation]:
        """Retrieve expired reservations."""
        pass
    
    @abstractmethod
    def delete(self, id: UUID) -> bool:
        """Delete a reservation."""
        pass


class StockMovementRepository(ABC):
    """Repository interface for StockMovement entity."""
    
    @abstractmethod
    def save(self, movement: StockMovement) -> StockMovement:
        """Save a movement record."""
        pass
    
    @abstractmethod
    def get_by_id(self, id: UUID) -> Optional[StockMovement]:
        """Retrieve movement by ID."""
        pass
    
    @abstractmethod
    def get_by_stock_item(self, stock_item_id: UUID, limit: int = 100) -> List[StockMovement]:
        """Retrieve movements for a stock item."""
        pass
    
    @abstractmethod
    def get_by_product(self, product_id: str, limit: int = 100) -> List[StockMovement]:
        """Retrieve movements for a product."""
        pass
    
    @abstractmethod
    def get_by_reference(self, reference_type: str, reference_id: str) -> List[StockMovement]:
        """Retrieve movements by reference (e.g., order_id, purchase_order_id)."""
        pass
