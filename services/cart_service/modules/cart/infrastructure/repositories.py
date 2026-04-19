"""
Repository implementations for Cart domain.

Concrete implementations using Django ORM.
"""
from typing import Optional
from uuid import UUID

from ..domain.entities import Cart, CartItem
from ..domain.repositories import CartRepository, CartItemRepository
from ..domain.enums import CartStatus
from ..domain.value_objects import Quantity, ProductReference, Price, ProductSnapshot

from .models import CartModel, CartItemModel


class DjangoCartRepository(CartRepository):
    """
    Django ORM implementation of CartRepository.
    """
    
    def save(self, cart: Cart) -> Cart:
        """Persist a cart."""
        cart_model = None
        if cart.status == CartStatus.ACTIVE:
            existing_active = self.get_active_cart_by_user(cart.user_id)
            if existing_active:
                cart_model = CartModel.objects.get(id=existing_active.id)
                cart.id = cart_model.id

        if cart_model is None:
            cart_model, _ = CartModel.objects.get_or_create(
                id=cart.id,
                defaults={
                    "user_id": cart.user_id,
                    "status": cart.status.value,
                    "currency": cart.currency,
                }
            )
        
        # Update fields
        cart_model.status = cart.status.value
        cart_model.currency = cart.currency
        cart_model.subtotal_amount = cart.subtotal_amount
        cart_model.total_quantity = cart.total_quantity
        cart_model.item_count = cart.item_count
        cart_model.save()
        
        return self._model_to_entity(cart_model)
    
    def get_by_id(self, cart_id: UUID) -> Optional[Cart]:
        """Get cart by ID."""
        try:
            cart_model = CartModel.objects.get(id=cart_id)
            return self._model_to_entity(cart_model)
        except CartModel.DoesNotExist:
            return None
    
    def get_active_cart_by_user(self, user_id: UUID) -> Optional[Cart]:
        """Get active cart for a user."""
        try:
            cart_model = CartModel.objects.filter(
                user_id=user_id,
                status=CartStatus.ACTIVE.value
            ).order_by("-updated_at", "-created_at").first()
            if not cart_model:
                return None
            return self._model_to_entity(cart_model)
        except CartModel.DoesNotExist:
            return None
    
    def list_user_carts(self, user_id: UUID) -> list[Cart]:
        """List all carts for a user."""
        cart_models = CartModel.objects.filter(user_id=user_id).order_by("-updated_at")
        return [self._model_to_entity(m) for m in cart_models]
    
    def delete(self, cart_id: UUID) -> None:
        """Delete a cart."""
        CartModel.objects.filter(id=cart_id).delete()
    
    def _model_to_entity(self, cart_model: CartModel) -> Cart:
        """Convert Django model to domain entity."""
        cart = Cart(
            id=cart_model.id,
            user_id=cart_model.user_id,
            status=CartStatus(cart_model.status),
            currency=cart_model.currency,
            created_at=cart_model.created_at,
            updated_at=cart_model.updated_at,
        )
        
        # Load items
        item_models = CartItemModel.objects.filter(cart=cart_model)
        for item_model in item_models:
            item = self._model_item_to_entity(item_model)
            key = f"{item.product_reference.product_id}#{item.product_reference.variant_id or ''}"
            cart._items[key] = item
        
        return cart
    
    def _model_item_to_entity(self, item_model: CartItemModel) -> CartItem:
        """Convert Django CartItemModel to CartItem entity."""
        product_ref = ProductReference(
            product_id=str(item_model.product_id),
            variant_id=str(item_model.variant_id) if item_model.variant_id else None
        )
        price = Price(item_model.unit_price_snapshot, item_model.currency)
        product_snapshot = ProductSnapshot(
            product_id=str(item_model.product_id),
            name=item_model.product_name_snapshot,
            slug=item_model.product_slug_snapshot,
            sku=item_model.sku,
            brand_name=item_model.brand_name_snapshot,
            category_name=item_model.category_name_snapshot,
            thumbnail_url=item_model.thumbnail_url_snapshot,
            variant_id=str(item_model.variant_id) if item_model.variant_id else None,
            variant_name=item_model.variant_name_snapshot,
            attributes_snapshot=item_model.attributes_snapshot,
        )
        
        from ..domain.enums import CartItemStatus
        return CartItem(
            id=item_model.id,
            cart_id=item_model.cart_id,
            product_reference=product_ref,
            quantity=Quantity(item_model.quantity),
            price_snapshot=price,
            product_snapshot=product_snapshot,
            status=CartItemStatus(item_model.status),
            availability_checked_at=item_model.availability_checked_at,
            created_at=item_model.created_at,
            updated_at=item_model.updated_at,
        )


class DjangoCartItemRepository(CartItemRepository):
    """
    Django ORM implementation of CartItemRepository.
    """
    
    def save(self, item: CartItem) -> CartItem:
        """Persist a cart item."""
        item_model, _ = CartItemModel.objects.get_or_create(
            id=item.id,
            defaults={
                "cart_id": item.cart_id,
                "product_id": item.product_reference.product_id,
                "variant_id": item.product_reference.variant_id,
                "quantity": item.quantity.value,
                "unit_price_snapshot": item.price_snapshot.amount,
                "currency": item.price_snapshot.currency,
                "product_name_snapshot": item.product_snapshot.name,
                "product_slug_snapshot": item.product_snapshot.slug,
                "variant_name_snapshot": item.product_snapshot.variant_name,
                "brand_name_snapshot": item.product_snapshot.brand_name,
                "category_name_snapshot": item.product_snapshot.category_name,
                "sku": item.product_snapshot.sku,
                "thumbnail_url_snapshot": item.product_snapshot.thumbnail_url,
                "attributes_snapshot": item.product_snapshot.attributes_snapshot,
                "status": item.status.value,
            }
        )
        
        # Update fields
        item_model.quantity = item.quantity.value
        item_model.unit_price_snapshot = item.price_snapshot.amount
        item_model.currency = item.price_snapshot.currency
        item_model.status = item.status.value
        item_model.availability_checked_at = item.availability_checked_at
        item_model.save()
        
        return item
    
    def get_by_id(self, item_id: UUID) -> Optional[CartItem]:
        """Get item by ID."""
        try:
            item_model = CartItemModel.objects.get(id=item_id)
            repo = DjangoCartRepository()
            return repo._model_item_to_entity(item_model)
        except CartItemModel.DoesNotExist:
            return None
    
    def list_by_cart(self, cart_id: UUID) -> list[CartItem]:
        """List all items in a cart."""
        item_models = CartItemModel.objects.filter(cart_id=cart_id)
        repo = DjangoCartRepository()
        return [repo._model_item_to_entity(m) for m in item_models]
    
    def delete(self, item_id: UUID) -> None:
        """Delete a cart item."""
        CartItemModel.objects.filter(id=item_id).delete()
    
    def delete_by_cart(self, cart_id: UUID) -> None:
        """Delete all items in a cart."""
        CartItemModel.objects.filter(cart_id=cart_id).delete()
