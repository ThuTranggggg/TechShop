"""
Domain services for Cart context.

Services that coordinate multiple entities or complex business logic.
"""
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4

from .entities import Cart, CartItem
from .value_objects import ProductReference, Quantity, Price, ProductSnapshot


class CartDomainService:
    """
    Domain service for complex cart operations that span multiple entities.
    """
    
    def __init__(self, cart_repository):
        """
        Initialize with repository for persisting changes.
        
        Args:
            cart_repository: Repository for Cart entities
        """
        self.cart_repository = cart_repository
    
    def ensure_user_active_cart(self, user_id: UUID) -> Cart:
        """
        Get existing active cart or create new one for user.
        
        Enforces business rule: each user has only one active cart.
        """
        existing_cart = self.cart_repository.get_active_cart_by_user(user_id)
        
        if existing_cart:
            return existing_cart
        
        # Create new active cart
        new_cart = Cart(id=uuid4(), user_id=user_id)
        return self.cart_repository.save(new_cart)
    
    def recalculate_cart_totals(self, cart: Cart) -> Dict[str, Any]:
        """
        Recalculate cart totals.
        
        Returns summary with item_count, total_quantity, subtotal_amount.
        """
        return {
            "item_count": cart.item_count,
            "total_quantity": cart.total_quantity,
            "subtotal_amount": float(cart.subtotal_amount),
            "currency": cart.currency,
        }
