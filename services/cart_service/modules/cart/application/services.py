"""
Application services for Cart context.

Services implement use cases, coordinating domain and infrastructure layers.
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import uuid4, UUID

from ..domain.entities import Cart, CartItem
from ..domain.value_objects import Quantity, ProductReference, Price, ProductSnapshot
from ..domain.enums import CartStatus, CartItemStatus
from ..domain.services import CartDomainService
from ..infrastructure.repositories import DjangoCartRepository, DjangoCartItemRepository
from ..infrastructure.clients import (
    get_product_service_client,
    get_inventory_service_client,
)

from .dtos import (
    CartResponseDTO,
    CartItemResponseDTO,
    AddItemToCartDTO,
    UpdateCartItemQuantityDTO,
    RemoveCartItemDTO,
    ClearCartDTO,
    ValidateCartDTO,
    RefreshCartDTO,
    CartValidationIssueDTO,
    CartValidationResultDTO,
)

logger = logging.getLogger(__name__)


class CartApplicationService:
    """
    Application service for Cart operations.
    
    Implements all cart-related use cases.
    """
    
    def __init__(self):
        self.cart_repository = DjangoCartRepository()
        self.item_repository = DjangoCartItemRepository()
        self.domain_service = CartDomainService(self.cart_repository)
        self.product_client = get_product_service_client()
        self.inventory_client = get_inventory_service_client()
    
    # ===== Use Cases =====
    
    def get_or_create_active_cart(self, user_id: str) -> CartResponseDTO:
        """Get existing active cart or create new one."""
        # Ensure user_id is UUID
        user_uuid = UUID(user_id)
        
        cart = self.domain_service.ensure_user_active_cart(user_uuid)
        return self._cart_to_response_dto(cart)
    
    def get_current_cart(self, user_id: str) -> CartResponseDTO:
        """Get current (active) cart for user."""
        user_uuid = UUID(user_id)
        cart = self.cart_repository.get_active_cart_by_user(user_uuid)
        
        if not cart:
            # Auto-create if doesn't exist
            return self.get_or_create_active_cart(user_id)
        
        return self._cart_to_response_dto(cart)
    
    def add_item_to_cart(self, dto: AddItemToCartDTO) -> CartResponseDTO:
        """Add item to cart."""
        user_uuid = UUID(dto.user_id)
        
        # Get or create active cart
        cart = self.domain_service.ensure_user_active_cart(user_uuid)
        
        # Validate quantity
        try:
            quantity = Quantity(dto.quantity)
        except ValueError as e:
            raise ValueError(f"Invalid quantity: {e}")
        
        # Get product snapshot from product_service
        product_snapshot = self.product_client.get_product_snapshot(
            dto.product_id,
            dto.variant_id
        )
        if not product_snapshot:
            raise ValueError(f"Product {dto.product_id} not found or invalid")
        
        # Check availability from inventory_service
        availability = self.inventory_client.check_availability([{
            "product_id": dto.product_id,
            "variant_id": dto.variant_id,
            "quantity": dto.quantity,
        }])
        
        if not availability.get("available"):
            raise ValueError("Insufficient inventory for this item")
        
        # Add item to cart
        product_reference = ProductReference(
            product_id=dto.product_id,
            variant_id=dto.variant_id
        )
        price = Price(product_snapshot.get("price", 0), cart.currency)
        
        item = cart.add_item(
            item_id=uuid4(),
            product_reference=product_reference,
            quantity=quantity,
            price_snapshot=price,
            product_snapshot=ProductSnapshot(
                product_id=dto.product_id,
                name=product_snapshot.get("name", ""),
                slug=product_snapshot.get("slug", ""),
                sku=product_snapshot.get("sku"),
                brand_name=product_snapshot.get("brand_name"),
                category_name=product_snapshot.get("category_name"),
                thumbnail_url=product_snapshot.get("thumbnail_url"),
                variant_id=dto.variant_id,
                variant_name=product_snapshot.get("variant_name"),
                attributes_snapshot=product_snapshot.get("attributes", {}),
            ),
        )
        
        # Persist
        self.cart_repository.save(cart)
        self.item_repository.save(item)
        
        return self._cart_to_response_dto(cart)
    
    def update_item_quantity(self, dto: UpdateCartItemQuantityDTO) -> CartResponseDTO:
        """Update quantity of a cart item."""
        user_uuid = UUID(dto.user_id)
        item_uuid = UUID(dto.item_id)
        
        # Get active cart
        cart = self.cart_repository.get_active_cart_by_user(user_uuid)
        if not cart:
            raise ValueError("Active cart not found")
        
        # Get item
        item = cart.get_item(item_uuid)
        if not item:
            raise ValueError("Item not found in cart")
        
        # Validate new quantity
        try:
            new_quantity = Quantity(dto.new_quantity)
        except ValueError as e:
            raise ValueError(f"Invalid quantity: {e}")
        
        # Check availability for new quantity
        availability = self.inventory_client.check_availability([{
            "product_id": str(item.product_reference.product_id),
            "variant_id": item.product_reference.variant_id,
            "quantity": dto.new_quantity,
        }])
        
        if not availability.get("available"):
            raise ValueError("Insufficient inventory for requested quantity")
        
        # Update quantity
        item.update_quantity(new_quantity)
        
        # Persist
        self.item_repository.save(item)
        self.cart_repository.save(cart)
        
        return self._cart_to_response_dto(cart)
    
    def remove_cart_item(self, dto: RemoveCartItemDTO) -> CartResponseDTO:
        """Remove item from cart."""
        user_uuid = UUID(dto.user_id)
        item_uuid = UUID(dto.item_id)
        
        # Get active cart
        cart = self.cart_repository.get_active_cart_by_user(user_uuid)
        if not cart:
            raise ValueError("Active cart not found")
        
        # Remove item
        cart.remove_item(item_uuid)
        
        # Persist
        self.item_repository.delete(item_uuid)
        self.cart_repository.save(cart)
        
        return self._cart_to_response_dto(cart)
    
    def clear_cart(self, dto: ClearCartDTO) -> CartResponseDTO:
        """Clear all items from cart."""
        user_uuid = UUID(dto.user_id)
        
        # Get active cart
        cart = self.cart_repository.get_active_cart_by_user(user_uuid)
        if not cart:
            raise ValueError("Active cart not found")
        
        # Clear items
        cart.clear()
        
        # Persist
        self.item_repository.delete_by_cart(cart.id)
        self.cart_repository.save(cart)
        
        return self._cart_to_response_dto(cart)
    
    def refresh_cart(self, dto: RefreshCartDTO) -> CartResponseDTO:
        """Refresh cart snapshots and availability."""
        user_uuid = UUID(dto.user_id)
        
        # Get active cart
        cart = self.cart_repository.get_active_cart_by_user(user_uuid)
        if not cart:
            raise ValueError("Active cart not found")
        
        # Refresh each item
        for item in cart.items:
            # Get latest product snapshot
            product_snapshot = self.product_client.get_product_snapshot(
                item.product_reference.product_id,
                item.product_reference.variant_id
            )
            
            if product_snapshot:
                new_snapshot = ProductSnapshot(
                    product_id=item.product_reference.product_id,
                    name=product_snapshot.get("name", ""),
                    slug=product_snapshot.get("slug", ""),
                    sku=product_snapshot.get("sku"),
                    brand_name=product_snapshot.get("brand_name"),
                    category_name=product_snapshot.get("category_name"),
                    thumbnail_url=product_snapshot.get("thumbnail_url"),
                    variant_id=item.product_reference.variant_id,
                    variant_name=product_snapshot.get("variant_name"),
                    attributes_snapshot=product_snapshot.get("attributes", {}),
                )
                item.update_snapshot(product_snapshot=new_snapshot)
            
            # Check availability
            availability = self.inventory_client.check_availability([{
                "product_id": item.product_reference.product_id,
                "variant_id": item.product_reference.variant_id,
                "quantity": item.quantity.value,
            }])
            
            if availability.get("available"):
                item.set_available()
            else:
                item.set_unavailable(CartItemStatus.OUT_OF_STOCK)
            
            item.availability_checked_at = datetime.utcnow()
            self.item_repository.save(item)
        
        # Recalculate totals
        self.cart_repository.save(cart)
        
        return self._cart_to_response_dto(cart)
    
    def validate_cart(self, dto: ValidateCartDTO) -> CartValidationResultDTO:
        """Validate all cart items."""
        user_uuid = UUID(dto.user_id)
        
        # Get active cart
        cart = self.cart_repository.get_active_cart_by_user(user_uuid)
        if not cart:
            raise ValueError("Active cart not found")
        
        issues = []
        
        for item in cart.items:
            # Check if product is still active
            if not self.product_client.validate_product_active(
                item.product_reference.product_id,
                item.product_reference.variant_id
            ):
                issues.append(CartValidationIssueDTO(
                    item_id=str(item.id),
                    product_id=item.product_reference.product_id,
                    status="product_inactive",
                    message="Product is no longer active or published",
                ))
                continue
            
            # Check inventory
            availability = self.inventory_client.check_availability([{
                "product_id": item.product_reference.product_id,
                "variant_id": item.product_reference.variant_id,
                "quantity": item.quantity.value,
            }])
            
            if not availability.get("available"):
                issues.append(CartValidationIssueDTO(
                    item_id=str(item.id),
                    product_id=item.product_reference.product_id,
                    status="out_of_stock",
                    message="Insufficient inventory for this item",
                ))
        
        is_valid = len(issues) == 0
        return CartValidationResultDTO(is_valid=is_valid, issues=issues)
    
    def checkout_preview(self, dto: ValidateCartDTO) -> Dict[str, Any]:
        """Build checkout preview with validation."""
        user_uuid = UUID(dto.user_id)
        
        # Get active cart
        cart = self.cart_repository.get_active_cart_by_user(user_uuid)
        if not cart:
            raise ValueError("Active cart not found")
        
        # Validate
        validation = self.validate_cart(dto)
        
        # Build checkout payload
        # IMPORTANT: Prices are returned as floats (JSON numeric), not strings
        # This ensures order_service can parse them correctly as Decimal without string conversion
        checkout_payload = {
            "cart_id": str(cart.id),
            "user_id": str(cart.user_id),
            "currency": cart.currency,
            "subtotal_amount": float(cart.subtotal_amount),  # Return as numeric, not string
            "items": [
                {
                    "cart_item_id": str(item.id),
                    "product_id": item.product_reference.product_id,
                    "variant_id": item.product_reference.variant_id,
                    "quantity": item.quantity.value,
                    "unit_price": float(item.price_snapshot.amount),  # Return as numeric, not string
                    "line_total": float(item.calculate_line_total().amount),  # Already numeric
                }
                for item in cart.items
            ],
        }
        
        return {
            "is_valid": validation.is_valid,
            "cart": self._cart_to_response_dto(cart).to_dict(),
            "issues": validation.to_dict()["issues"],
            "checkout_payload": checkout_payload if validation.is_valid else None,
        }
    
    def mark_checked_out(self, cart_id: str) -> CartResponseDTO:
        """Mark cart as checked out (internal use)."""
        cart_uuid = UUID(cart_id)
        
        cart = self.cart_repository.get_by_id(cart_uuid)
        if not cart:
            raise ValueError("Cart not found")
        
        cart.mark_checked_out()
        self.cart_repository.save(cart)
        
        return self._cart_to_response_dto(cart)
    
    # ===== Helper Methods =====
    
    def _cart_to_response_dto(self, cart: Cart) -> CartResponseDTO:
        """Convert Cart entity to response DTO."""
        items = [self._item_to_response_dto(item) for item in cart.items]
        
        return CartResponseDTO(
            id=str(cart.id),
            user_id=str(cart.user_id),
            status=cart.status.value,
            currency=cart.currency,
            subtotal_amount=str(cart.subtotal_amount),
            total_quantity=cart.total_quantity,
            item_count=cart.item_count,
            items=items,
            last_activity_at=cart.last_activity_at.isoformat() if cart.last_activity_at else None,
            created_at=cart.created_at.isoformat() if cart.created_at else None,
            updated_at=cart.updated_at.isoformat() if cart.updated_at else None,
        )
    
    def _item_to_response_dto(self, item: CartItem) -> CartItemResponseDTO:
        """Convert CartItem entity to response DTO."""
        line_total = item.calculate_line_total()
        
        return CartItemResponseDTO(
            id=str(item.id),
            product_id=item.product_reference.product_id,
            variant_id=item.product_reference.variant_id,
            product_name=item.product_snapshot.name,
            product_slug=item.product_snapshot.slug,
            variant_name=item.product_snapshot.variant_name,
            brand_name=item.product_snapshot.brand_name,
            category_name=item.product_snapshot.category_name,
            sku=item.product_snapshot.sku,
            thumbnail_url=item.product_snapshot.thumbnail_url,
            quantity=item.quantity.value,
            unit_price=str(item.price_snapshot.amount),
            currency=item.price_snapshot.currency,
            line_total=str(line_total.amount),
            status=item.status.value,
            availability_checked_at=item.availability_checked_at.isoformat() if item.availability_checked_at else None,
        )


# Factory function
def get_cart_application_service() -> CartApplicationService:
    """Get cart application service."""
    return CartApplicationService()
