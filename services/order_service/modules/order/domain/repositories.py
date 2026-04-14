"""
Domain repositories and interfaces for Order context.

Defines repository contracts for persistence.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from .entities import Order, OrderItem
from .enums import OrderStatus


class OrderRepository(ABC):
    """
    Repository interface for Order aggregate.
    """
    
    @abstractmethod
    def save(self, order: Order) -> None:
        """Save or update an order."""
        pass
    
    @abstractmethod
    def get_by_id(self, order_id: UUID) -> Optional[Order]:
        """Get order by ID."""
        pass
    
    @abstractmethod
    def get_by_order_number(self, order_number: str) -> Optional[Order]:
        """Get order by order number."""
        pass
    
    @abstractmethod
    def get_user_orders(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Order]:
        """Get all orders for a specific user."""
        pass
    
    @abstractmethod
    def get_orders_by_status(
        self,
        status: OrderStatus,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Order]:
        """Get orders filtered by status."""
        pass
    
    @abstractmethod
    def get_orders_by_payment_status(
        self,
        payment_status: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Order]:
        """Get orders filtered by payment status."""
        pass
    
    @abstractmethod
    def count(self) -> int:
        """Total count of orders."""
        pass
    
    @abstractmethod
    def count_user_orders(self, user_id: UUID) -> int:
        """Count orders for a specific user."""
        pass


class OrderItemRepository(ABC):
    """
    Repository interface for OrderItem.
    """
    
    @abstractmethod
    def save(self, item: OrderItem) -> None:
        """Save or update an order item."""
        pass
    
    @abstractmethod
    def get_by_id(self, item_id: UUID) -> Optional[OrderItem]:
        """Get order item by ID."""
        pass
    
    @abstractmethod
    def get_by_order_id(self, order_id: UUID) -> List[OrderItem]:
        """Get all items for an order."""
        pass
    
    @abstractmethod
    def delete(self, item_id: UUID) -> None:
        """Delete an order item."""
        pass
