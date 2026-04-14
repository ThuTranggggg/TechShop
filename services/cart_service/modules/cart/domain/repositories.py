"""
Repository interfaces (contracts) for Cart domain.

Repositories are contracts between domain and infrastructure layers.
Concrete implementations exist in infrastructure layer.
"""
from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from .entities import Cart, CartItem


class CartRepository(ABC):
    """
    Repository interface for Cart aggregate root.
    """
    
    @abstractmethod
    def save(self, cart: Cart) -> Cart:
        """Persist a cart."""
        pass
    
    @abstractmethod
    def get_by_id(self, cart_id: UUID) -> Optional[Cart]:
        """Get cart by ID."""
        pass
    
    @abstractmethod
    def get_active_cart_by_user(self, user_id: UUID) -> Optional[Cart]:
        """Get active cart for a user."""
        pass
    
    @abstractmethod
    def list_user_carts(self, user_id: UUID) -> list[Cart]:
        """List all carts for a user."""
        pass
    
    @abstractmethod
    def delete(self, cart_id: UUID) -> None:
        """Delete a cart."""
        pass


class CartItemRepository(ABC):
    """
    Repository interface for CartItem entities.
    """
    
    @abstractmethod
    def save(self, item: CartItem) -> CartItem:
        """Persist a cart item."""
        pass
    
    @abstractmethod
    def get_by_id(self, item_id: UUID) -> Optional[CartItem]:
        """Get item by ID."""
        pass
    
    @abstractmethod
    def list_by_cart(self, cart_id: UUID) -> list[CartItem]:
        """List all items in a cart."""
        pass
    
    @abstractmethod
    def delete(self, item_id: UUID) -> None:
        """Delete a cart item."""
        pass
    
    @abstractmethod
    def delete_by_cart(self, cart_id: UUID) -> None:
        """Delete all items in a cart."""
        pass
