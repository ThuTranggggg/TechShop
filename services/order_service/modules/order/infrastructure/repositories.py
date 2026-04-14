"""
Infrastructure repository implementations.

Implements domain repository interfaces using Django ORM.
"""

from typing import List, Optional
from uuid import UUID
from decimal import Decimal

from django.db.models import QuerySet, F

from ..domain import (
    Order, OrderItem, OrderRepository, OrderItemRepository, OrderStatus,
    Money, OrderNumber, ProductReference, AddressSnapshot, CustomerSnapshot,
    ProductSnapshot, Currency
)
from .models import OrderModel, OrderItemModel, OrderStatusHistoryModel


class OrderRepositoryImpl(OrderRepository):
    """
    Implementation of OrderRepository using Django ORM.
    """
    
    def save(self, order: Order) -> None:
        """Save or update order to database."""
        order_model = self._order_to_model(order)
        order_model.save()
    
    def get_by_id(self, order_id: UUID) -> Optional[Order]:
        """Retrieve order by ID."""
        try:
            model = OrderModel.objects.get(id=order_id)
            return self._model_to_order(model)
        except OrderModel.DoesNotExist:
            return None
    
    def get_by_order_number(self, order_number: str) -> Optional[Order]:
        """Retrieve order by order number."""
        try:
            model = OrderModel.objects.get(order_number=order_number)
            return self._model_to_order(model)
        except OrderModel.DoesNotExist:
            return None
    
    def get_user_orders(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Order]:
        """Get all orders for a user."""
        models = OrderModel.objects.filter(user_id=user_id).order_by("-created_at")[offset: offset + limit]
        return [self._model_to_order(m) for m in models]
    
    def get_orders_by_status(
        self,
        status: OrderStatus,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Order]:
        """Get orders filtered by status."""
        models = OrderModel.objects.filter(status=status.value).order_by("-created_at")[offset: offset + limit]
        return [self._model_to_order(m) for m in models]
    
    def get_orders_by_payment_status(
        self,
        payment_status: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Order]:
        """Get orders filtered by payment status."""
        models = OrderModel.objects.filter(payment_status=payment_status).order_by("-created_at")[offset: offset + limit]
        return [self._model_to_order(m) for m in models]
    
    def count(self) -> int:
        """Total order count."""
        return OrderModel.objects.count()
    
    def count_user_orders(self, user_id: UUID) -> int:
        """Count orders for user."""
        return OrderModel.objects.filter(user_id=user_id).count()
    
    def _order_to_model(self, order: Order) -> OrderModel:
        """Convert domain Order to ORM model."""
        return OrderModel(
            id=order.id,
            order_number=order.order_number.value,
            user_id=order.user_id,
            cart_id=order.cart_id,
            status=order.status.value,
            payment_status=order.payment_status.value,
            fulfillment_status=order.fulfillment_status.value,
            currency=order.currency.value,
            subtotal_amount=order.subtotal.amount,
            shipping_fee_amount=order.shipping_fee.amount,
            discount_amount=order.discount.amount,
            tax_amount=order.tax.amount,
            grand_total_amount=order.grand_total.amount,
            total_quantity=order.total_quantity,
            item_count=order.item_count,
            customer_name_snapshot=order.customer_snapshot.name,
            customer_email_snapshot=order.customer_snapshot.email,
            customer_phone_snapshot=order.customer_snapshot.phone or "",
            receiver_name=order.address_snapshot.receiver_name,
            receiver_phone=order.address_snapshot.receiver_phone,
            shipping_line1=order.address_snapshot.line1,
            shipping_line2=order.address_snapshot.line2 or "",
            shipping_ward=order.address_snapshot.ward or "",
            shipping_district=order.address_snapshot.district,
            shipping_city=order.address_snapshot.city,
            shipping_country=order.address_snapshot.country or "Vietnam",
            shipping_postal_code=order.address_snapshot.postal_code or "",
            payment_id=order.payment_id,
            payment_reference=order.payment_reference or "",
            shipment_id=order.shipment_id,
            shipment_reference=order.shipment_reference or "",
            stock_reservation_refs=order.stock_reservation_refs,
            notes=order.notes,
            placed_at=order.placed_at,
            paid_at=order.paid_at,
            cancelled_at=order.cancelled_at,
            completed_at=order.completed_at,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )
    
    def _model_to_order(self, model: OrderModel) -> Order:
        """Convert ORM model to domain Order."""
        # Get items
        item_models = OrderItemModel.objects.filter(order_id=model.id)
        items = [self._item_model_to_entity(im) for im in item_models]
        
        # Reconstruct order
        customer = CustomerSnapshot(
            name=model.customer_name_snapshot,
            email=model.customer_email_snapshot,
            phone=model.customer_phone_snapshot or None,
            user_id=model.user_id,
        )
        
        address = AddressSnapshot(
            receiver_name=model.receiver_name,
            receiver_phone=model.receiver_phone,
            line1=model.shipping_line1,
            line2=model.shipping_line2 or None,
            ward=model.shipping_ward or None,
            district=model.shipping_district,
            city=model.shipping_city,
            country=model.shipping_country,
            postal_code=model.shipping_postal_code or None,
        )
        
        order = Order(
            id=model.id,
            order_number=OrderNumber(model.order_number),
            user_id=model.user_id,
            cart_id=model.cart_id,
            currency=Currency[model.currency],
            customer_snapshot=customer,
            address_snapshot=address,
            status=OrderStatus(model.status),
            payment_status=PaymentStatus(model.payment_status),
            fulfillment_status=FulfillmentStatus(model.fulfillment_status),
            items=items,
            subtotal=Money(model.subtotal_amount, Currency[model.currency]),
            shipping_fee=Money(model.shipping_fee_amount, Currency[model.currency]),
            discount=Money(model.discount_amount, Currency[model.currency]),
            tax=Money(model.tax_amount, Currency[model.currency]),
            grand_total=Money(model.grand_total_amount, Currency[model.currency]),
            total_quantity=model.total_quantity,
            item_count=model.item_count,
            notes=model.notes,
            payment_id=model.payment_id,
            payment_reference=model.payment_reference or None,
            shipment_id=model.shipment_id,
            shipment_reference=model.shipment_reference or None,
            stock_reservation_refs=model.stock_reservation_refs,
            placed_at=model.placed_at,
            paid_at=model.paid_at,
            cancelled_at=model.cancelled_at,
            completed_at=model.completed_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
        
        return order
    
    def _item_model_to_entity(self, model: OrderItemModel) -> OrderItem:
        """Convert ORM model to domain OrderItem."""
        product_ref = ProductReference(
            product_id=model.product_id,
            variant_id=model.variant_id,
            sku=model.sku or None,
        )
        
        product_snapshot = ProductSnapshot(
            product_id=model.product_id,
            name=model.product_name_snapshot,
            slug=model.product_slug_snapshot,
            thumbnail_url=model.thumbnail_url_snapshot or None,
            brand_name=model.brand_name_snapshot or None,
            category_name=model.category_name_snapshot or None,
            variant_name=model.variant_name_snapshot or None,
            sku=model.sku or None,
            attributes=model.attributes_snapshot,
        )
        
        return OrderItem(
            id=model.id,
            order_id=model.order_id,
            product_reference=product_ref,
            product_snapshot=product_snapshot,
            quantity=model.quantity,
            unit_price=Money(model.unit_price, Currency[model.currency]),
            currency=Currency[model.currency],
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class OrderItemRepositoryImpl(OrderItemRepository):
    """
    Implementation of OrderItemRepository using Django ORM.
    """
    
    def save(self, item: OrderItem) -> None:
        """Save or update order item."""
        model = self._entity_to_model(item)
        model.save()
    
    def get_by_id(self, item_id: UUID) -> Optional[OrderItem]:
        """Get item by ID."""
        try:
            model = OrderItemModel.objects.get(id=item_id)
            return self._model_to_entity(model)
        except OrderItemModel.DoesNotExist:
            return None
    
    def get_by_order_id(self, order_id: UUID) -> List[OrderItem]:
        """Get all items for an order."""
        models = OrderItemModel.objects.filter(order_id=order_id).order_by("created_at")
        return [self._model_to_entity(m) for m in models]
    
    def delete(self, item_id: UUID) -> None:
        """Delete item by ID."""
        OrderItemModel.objects.filter(id=item_id).delete()
    
    def _entity_to_model(self, item: OrderItem) -> OrderItemModel:
        """Convert domain OrderItem to ORM model."""
        return OrderItemModel(
            id=item.id,
            order_id=item.order_id,
            product_id=item.product_reference.product_id,
            variant_id=item.product_reference.variant_id,
            sku=item.product_reference.sku or "",
            quantity=item.quantity,
            unit_price=item.unit_price.amount,
            line_total=item.line_total.amount,
            currency=item.currency.value,
            product_name_snapshot=item.product_snapshot.name,
            product_slug_snapshot=item.product_snapshot.slug,
            variant_name_snapshot=item.product_snapshot.variant_name or "",
            brand_name_snapshot=item.product_snapshot.brand_name or "",
            category_name_snapshot=item.product_snapshot.category_name or "",
            thumbnail_url_snapshot=item.product_snapshot.thumbnail_url or "",
            attributes_snapshot=item.product_snapshot.attributes or {},
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
    
    def _model_to_entity(self, model: OrderItemModel) -> OrderItem:
        """Convert ORM model to domain OrderItem."""
        product_ref = ProductReference(
            product_id=model.product_id,
            variant_id=model.variant_id,
            sku=model.sku or None,
        )
        
        product_snapshot = ProductSnapshot(
            product_id=model.product_id,
            name=model.product_name_snapshot,
            slug=model.product_slug_snapshot,
            thumbnail_url=model.thumbnail_url_snapshot or None,
            brand_name=model.brand_name_snapshot or None,
            category_name=model.category_name_snapshot or None,
            variant_name=model.variant_name_snapshot or None,
            sku=model.sku or None,
            attributes=model.attributes_snapshot,
        )
        
        return OrderItem(
            id=model.id,
            order_id=model.order_id,
            product_reference=product_ref,
            product_snapshot=product_snapshot,
            quantity=model.quantity,
            unit_price=Money(model.unit_price, Currency[model.currency]),
            currency=Currency[model.currency],
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


# Import enums after class definitions to avoid circular imports
from ..domain import PaymentStatus, FulfillmentStatus
