"""
Application services for Order context.

Use cases and orchestration logic for order operations.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID, uuid4
from decimal import Decimal
from datetime import datetime

from django.db import transaction

from ..domain import (
    Order, OrderItem, OrderStatus, PaymentStatus, FulfillmentStatus, Currency,
    OrderNumber, ProductReference, AddressSnapshot, CustomerSnapshot,
    ProductSnapshot, Money, OrderNumberGenerator, OrderValidator,
    OrderStateTransitionService, OrderCalculationService,
    OrderRepository, OrderItemRepository
)
from ..infrastructure import (
    OrderRepositoryImpl, OrderItemRepositoryImpl,
    CartServiceClient, InventoryServiceClient, PaymentServiceClient,
    ShippingServiceClient, OrderStatusHistoryModel
)
from .dtos import (
    OrderDetailDTO, OrderListItemDTO, OrderItemDTO, StatusHistoryItemDTO,
    order_to_detail_dto, order_to_list_dto, order_item_to_dto, OrderTimelineDTO
)

logger = logging.getLogger(__name__)


class GetUserOrdersService:
    """Get all orders for a user."""
    
    def __init__(self, order_repo: OrderRepository = None):
        self.order_repo = order_repo or OrderRepositoryImpl()
    
    def execute(self, user_id: UUID, limit: int = 50, offset: int = 0) -> Tuple[List[OrderListItemDTO], int]:
        """
        Get user orders.
        
        Returns (order_list, total_count).
        """
        orders = self.order_repo.get_user_orders(user_id, limit, offset)
        total = self.order_repo.count_user_orders(user_id)
        
        order_dtos = [order_to_list_dto(order) for order in orders]
        return order_dtos, total


class GetOrderDetailService:
    """Get single order full details."""
    
    def __init__(self, order_repo: OrderRepository = None):
        self.order_repo = order_repo or OrderRepositoryImpl()
    
    def execute(self, order_id: UUID) -> Optional[OrderDetailDTO]:
        """Get order by ID."""
        order = self.order_repo.get_by_id(order_id)
        if not order:
            return None
        
        item_dtos = [order_item_to_dto(item) for item in order.items]
        return order_to_detail_dto(order, item_dtos)


class GetOrderTimelineService:
    """Get order status timeline."""
    
    def execute(self, order_id: UUID) -> Optional[OrderTimelineDTO]:
        """Get order timeline from status history."""
        try:
            from ...infrastructure.models import OrderModel, OrderStatusHistoryModel
            
            order = OrderModel.objects.get(id=order_id)
            history_models = OrderStatusHistoryModel.objects.filter(order_id=order_id).order_by("created_at")
            
            history_items = [
                StatusHistoryItemDTO(
                    from_status=h.from_status,
                    to_status=h.to_status,
                    note=h.note,
                    changed_by=h.changed_by,
                    created_at=h.created_at,
                )
                for h in history_models
            ]
            
            return OrderTimelineDTO(
                order_id=order_id,
                order_number=order.order_number,
                status_history=history_items,
                placed_at=order.placed_at,
                paid_at=order.paid_at,
                shipped_at=order.placed_at,  # Approximation
                delivered_at=None,  # Would need to parse history
                completed_at=order.completed_at,
                cancelled_at=order.cancelled_at,
            )
        except Exception as e:
            logger.error(f"Failed to get timeline for order {order_id}: {e}")
            return None


class CreateOrderFromCartService:
    """
    Main service for creating order from cart.
    
    Orchestrates multiple steps:
    1. Validate cart
    2. Build checkout payload
    3. Validate shipping address
    4. Reserve stock
    5. Create payment
    6. Mark cart checked out
    """
    
    def __init__(
        self,
        order_repo: OrderRepository = None,
        item_repo: OrderItemRepository = None,
        cart_client: CartServiceClient = None,
        inventory_client: InventoryServiceClient = None,
        payment_client: PaymentServiceClient = None,
        user_client = None,
    ):
        self.order_repo = order_repo or OrderRepositoryImpl()
        self.item_repo = item_repo or OrderItemRepositoryImpl()
        self.state_service = OrderStateTransitionService(self.order_repo)
        self.calc_service = OrderCalculationService()
        self.cart_client = cart_client or CartServiceClient()
        self.inventory_client = inventory_client or InventoryServiceClient()
        self.payment_client = payment_client or PaymentServiceClient()
        # Lazy import to avoid circular dependencies
        if user_client is None:
            from ...infrastructure.clients import UserServiceClient
            user_client = UserServiceClient()
        self.user_client = user_client
    
    @transaction.atomic
    def execute(
        self,
        user_id: UUID,
        cart_id: UUID,
        shipping_address: Dict[str, Any],
        notes: Optional[str] = None,
    ) -> OrderDetailDTO:
        """
        Create order from cart with shipping address validation.
        
        Raises ValueError if any step fails.
        """
        try:
            # 1. Validate cart and get checkout payload
            logger.info(f"Creating order from cart {cart_id} for user {user_id}")
            
            checkout_payload = self.cart_client.build_checkout_payload(cart_id, user_id)
            logger.debug(f"Checkout payload: {checkout_payload}")
            
            # 2. Validate payload
            OrderValidator.validate_checkout_payload(checkout_payload)
            
            # 3. Validate shipping address (non-blocking)
            address_validation = self._validate_shipping_address(user_id, shipping_address)
            
            # 4. Create Order aggregate
            order = self._build_order_from_payload(
                user_id=user_id,
                cart_id=cart_id,
                checkout_payload=checkout_payload,
                shipping_address=shipping_address,
                notes=notes,
            )
            
            # 5. Reserve stock
            reservation_ids = self._reserve_stock(order)
            
            # 6. Create payment
            payment_info = self._create_payment(order)
            
            # 7. Save order with references
            order.set_payment_info(
                payment_id=UUID(payment_info.get("payment_id")),
                payment_reference=payment_info.get("payment_reference", ""),
            )
            order.stock_reservation_refs = [
                {"id": rid, "item_id": None} for rid in reservation_ids
            ]
            
            # 8. Transition to awaiting_payment
            order.mark_awaiting_payment(payment_info.get("payment_reference", ""))
            
            # 9. Save/persist
            self.order_repo.save(order)
            
            # Save items
            for item in order.items:
                self.item_repo.save(item)
            
            # 10. Update address verification flag if needed (non-blocking)
            if not address_validation["is_valid"]:
                self._update_address_verification(
                    order_id=order.id,
                    requires_verification=True,
                    note=address_validation.get("message", "Address validation failed")
                )
            
            # 11. Mark cart checked out
            try:
                self.cart_client.mark_cart_checked_out(cart_id)
            except Exception as e:
                logger.warning(f"Failed to mark cart checked out: {e}")
            
            # 12. Record status history
            self._record_status_history(
                order_id=order.id,
                from_status=None,
                to_status=OrderStatus.AWAITING_PAYMENT.value,
                note="Order created from cart, stock reserved, payment initiated",
            )
            
            logger.info(f"Order {order.order_number} created successfully")
            
            # Return DTO
            item_dtos = [order_item_to_dto(item) for item in order.items]
            return order_to_detail_dto(order, item_dtos)
        
        except Exception as e:
            logger.error(f"Failed to create order from cart: {e}")
            # TODO: Rollback reservations if partial failure
            raise
    
    def _build_order_from_payload(
        self,
        user_id: UUID,
        cart_id: UUID,
        checkout_payload: Dict[str, Any],
        shipping_address: Dict[str, Any],
        notes: Optional[str] = None,
    ) -> Order:
        """Build Order domain object from checkout payload."""
        
        # Generate order number
        # TODO: Get next sequence number from DB
        order_number = OrderNumberGenerator.generate(1)
        
        # Build customer snapshot
        customer_data = checkout_payload.get("customer", {})
        customer = CustomerSnapshot(
            name=customer_data.get("name", ""),
            email=customer_data.get("email", ""),
            phone=customer_data.get("phone"),
            user_id=user_id,
        )
        
        # Build address snapshot
        address = AddressSnapshot(
            receiver_name=shipping_address.get("receiver_name", ""),
            receiver_phone=shipping_address.get("receiver_phone", ""),
            line1=shipping_address.get("line1", ""),
            line2=shipping_address.get("line2"),
            ward=shipping_address.get("ward"),
            district=shipping_address.get("district", ""),
            city=shipping_address.get("city", ""),
            country=shipping_address.get("country", "Vietnam"),
            postal_code=shipping_address.get("postal_code"),
        )
        
        # Determine currency
        currency = Currency.VND  # TODO: From payload if available
        
        # Create order
        order = Order(
            id=uuid4(),
            order_number=order_number,
            user_id=user_id,
            cart_id=cart_id,
            currency=currency,
            customer_snapshot=customer,
            address_snapshot=address,
            notes=notes or "",
            status=OrderStatus.PENDING,
            payment_status=PaymentStatus.UNPAID,
            fulfillment_status=FulfillmentStatus.UNFULFILLED,
        )
        
        # Build order items from payload
        items_data = checkout_payload.get("items", [])
        for item_data in items_data:
            item = self._build_order_item(order.id, item_data, currency)
            order.add_item(item)
        
        return order
    
    def _build_order_item(
        self,
        order_id: UUID,
        item_data: Dict[str, Any],
        currency: Currency,
    ) -> OrderItem:
        """Build OrderItem from item data."""
        
        product_ref = ProductReference(
            product_id=UUID(item_data["product_id"]),
            variant_id=UUID(item_data["variant_id"]) if item_data.get("variant_id") else None,
            sku=item_data.get("sku"),
        )
        
        product_snapshot = ProductSnapshot(
            product_id=UUID(item_data["product_id"]),
            name=item_data.get("product_name", ""),
            slug=item_data.get("product_slug", ""),
            thumbnail_url=item_data.get("thumbnail_url"),
            brand_name=item_data.get("brand_name"),
            category_name=item_data.get("category_name"),
            variant_name=item_data.get("variant_name"),
            sku=item_data.get("sku"),
            attributes=item_data.get("attributes", {}),
        )
        
        unit_price = Money(
            Decimal(str(item_data.get("unit_price", "0"))),
            currency
        )
        
        return OrderItem(
            id=uuid4(),
            order_id=order_id,
            product_reference=product_ref,
            product_snapshot=product_snapshot,
            quantity=item_data.get("quantity", 0),
            unit_price=unit_price,
            currency=currency,
        )
    
    def _reserve_stock(self, order: Order) -> List[str]:
        """Reserve stock for all order items."""
        items_to_reserve = [
            {
                "product_id": str(item.product_reference.product_id),
                "variant_id": str(item.product_reference.variant_id) if item.product_reference.variant_id else None,
                "quantity": item.quantity,
            }
            for item in order.items
        ]
        
        result = self.inventory_client.create_reservations(
            items=items_to_reserve,
            order_id=order.id,
            user_id=order.user_id,
        )
        
        # Extract reservation IDs
        reservation_ids = result.get("reservation_ids", [])
        if not reservation_ids:
            raise ValueError("No reservation IDs returned from inventory service")
        
        return reservation_ids
    
    def _create_payment(self, order: Order) -> Dict[str, Any]:
        """Create payment request."""
        result = self.payment_client.create_payment(
            order_id=order.id,
            user_id=order.user_id,
            amount=order.grand_total.amount,
            currency=order.currency.value,
            order_number=order.order_number.value,
            metadata={
                "items_count": order.item_count,
                "sender": "order_service",
            },
        )
        
        if not result.get("payment_id"):
            raise ValueError("No payment_id returned from payment service")
        
        return result
    
    def _validate_shipping_address(
        self,
        user_id: UUID,
        shipping_address: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate shipping address against user's known addresses.
        
        Non-blocking validation: Returns validation result for flagging orders.
        """
        try:
            result = self.user_client.validate_user_address(user_id, shipping_address)
            if result.get("is_valid"):
                logger.info(f"Shipping address validated for user {user_id}")
            else:
                logger.warning(f"Shipping address validation failed for user {user_id}: {result.get('message')}")
            return result
        except Exception as e:
            logger.warning(f"Exception during address validation: {e}")
            return {"is_valid": False, "message": str(e)}
    
    def _update_address_verification(
        self,
        order_id: UUID,
        requires_verification: bool,
        note: str = "",
    ) -> None:
        """
        Update order with address verification flag.
        
        Used when address validation fails (non-blocking).
        """
        try:
            from ...infrastructure.models import OrderModel
            OrderModel.objects.filter(id=order_id).update(
                address_requires_verification=requires_verification,
                address_verification_note=note,
            )
            logger.info(f"Updated address verification flag for order {order_id}: {requires_verification}")
        except Exception as e:
            logger.warning(f"Failed to update address verification flag: {e}")
    
    def _record_status_history(
        self,
        order_id: UUID,
        from_status: Optional[str],
        to_status: str,
        note: str = "",
    ) -> None:
        """Record status transition in history."""
        OrderStatusHistoryModel.objects.create(
            order_id=order_id,
            from_status=from_status,
            to_status=to_status,
            note=note,
            metadata={},
        )


class HandlePaymentSuccessService:
    """Handle successful payment callback."""
    
    def __init__(
        self,
        order_repo: OrderRepository = None,
        inventory_client: InventoryServiceClient = None,
        payment_client: PaymentServiceClient = None,
        shipping_client: ShippingServiceClient = None,
        ai_client = None,
    ):
        self.order_repo = order_repo or OrderRepositoryImpl()
        self.state_service = OrderStateTransitionService(self.order_repo)
        self.inventory_client = inventory_client or InventoryServiceClient()
        self.payment_client = payment_client or PaymentServiceClient()
        self.shipping_client = shipping_client or ShippingServiceClient()
        # Lazy import to avoid circular dependencies
        if ai_client is None:
            from ...infrastructure.clients import AIServiceClient
            ai_client = AIServiceClient()
        self.ai_client = ai_client
    
    @transaction.atomic
    def execute(self, order_id: UUID, payment_id: UUID) -> OrderDetailDTO:
        """
        Handle payment success callback with idempotency.
        
        IDEMPOTENCY: If payment_success was already processed, returns early (200 OK).
        This prevents double-confirming stock reservations when payment callbacks fire multiple times.
        
        CRITICAL ERROR RECOVERY:
        1. Try to confirm stock reservations
        2. If reservation confirmation FAILS:
           - Release inventory
           - Refund payment (compensating transaction)
           - Set order to PAYMENT_FAILED
           - Log clearly for debugging
        3. If all succeeds:
           - Update order status to PAID
           - Emit order_created event to AI service (non-blocking)
           - Record history
        
        Raises ValueError if order not found or state mismatch.
        """
        from django.utils import timezone
        
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise ValueError(f"Order not found: {order_id}")
        
        if order.status != OrderStatus.AWAITING_PAYMENT:
            raise ValueError(f"Order not in awaiting_payment status: {order.status}")
        
        # IDEMPOTENCY CHECK: If payment success was already processed, return early
        if order.payment_success_processed_at is not None:
            logger.info(
                f"Payment success already processed for order {order_id} at {order.payment_success_processed_at}. "
                f"Skipping idempotent callback."
            )
            item_dtos = [order_item_to_dto(item) for item in order.items]
            return order_to_detail_dto(order, item_dtos)
        
        # Extract reservation IDs
        reservation_ids = [
            ref.get("id") for ref in order.stock_reservation_refs
            if ref.get("id")
        ]
        
        try:
            # Try to confirm reservations
            if reservation_ids:
                logger.info(f"Confirming {len(reservation_ids)} reservations for order {order_id}")
                self.inventory_client.confirm_reservations(reservation_ids, order_id)
            
            # Update order to PAID
            logger.info(f"Payment {payment_id} confirmed, marking order {order_id} as PAID")
            self.state_service.handle_payment_success(order)
            
            # Mark payment_success as processed (for idempotency)
            from ...infrastructure.models import OrderModel
            OrderModel.objects.filter(id=order_id).update(
                payment_success_processed_at=timezone.now()
            )
            
            # Record history
            self._record_status_history(
                order_id=order_id,
                from_status=OrderStatus.AWAITING_PAYMENT.value,
                to_status=OrderStatus.PAID.value,
                note=f"Payment {payment_id} confirmed and stock reserved",
            )
            
            # Emit order_created event to AI service (non-blocking)
            self._emit_order_event_to_ai(order, "payment_success")
            
            logger.info(f"Order {order_id} payment processed successfully")
            
        except Exception as inventory_error:
            # CRITICAL: Inventory confirmation failed - trigger compensating transaction
            logger.error(
                f"CRITICAL: Inventory confirmation failed for order {order_id}: {inventory_error}"
            )
            
            try:
                # Step 1: Release the reservations
                if reservation_ids:
                    logger.warning(f"Releasing {len(reservation_ids)} reservations due to inventory error")
                    self.inventory_client.release_reservations(
                        reservation_ids,
                        order_id,
                        reason=f"Inventory confirmation failed: {str(inventory_error)}"
                    )
            except Exception as release_error:
                logger.error(f"CRITICAL: Failed to release reservations: {release_error}")
            
            try:
                # Step 2: Refund the payment
                logger.warning(f"Refunding payment {payment_id} due to inventory failure")
                self.payment_client.refund_payment(
                    payment_id,
                    reason=f"Inventory confirmation failed: {str(inventory_error)}",
                    metadata={
                        "order_id": str(order_id),
                        "error": str(inventory_error),
                    }
                )
            except Exception as refund_error:
                logger.error(f"CRITICAL: Failed to refund payment: {refund_error}")
                # Continue to update order status despite refund failure
            
            # Step 3: Mark order as PAYMENT_FAILED
            logger.info(f"Marking order {order_id} status as PAYMENT_FAILED")
            try:
                self.state_service.handle_payment_failure(order)
            except Exception as e:
                logger.error(f"Failed to update order status: {e}")
                raise
            
            # Record history
            self._record_status_history(
                order_id=order_id,
                from_status=OrderStatus.AWAITING_PAYMENT.value,
                to_status=OrderStatus.PAYMENT_FAILED.value,
                note=f"Payment succeeded but inventory confirmation failed. Refund triggered. Error: {str(inventory_error)}",
            )
            
            # Log comprehensive error for operations team
            logger.critical(
                f"INVENTORY_CONFIRMATION_ERROR: order_id={order_id}, "
                f"payment_id={payment_id}, "
                f"error={str(inventory_error)},    "
                f"action=refund_triggered"
            )
            
            raise ValueError(
                f"Payment succeeded but inventory confirmation failed. "
                f"Refund has been triggered. Order: {order_id}"
            )
        
        # Return updated DTO
        order = self.order_repo.get_by_id(order_id)
        item_dtos = [order_item_to_dto(item) for item in order.items]
        return order_to_detail_dto(order, item_dtos)
    
    def _emit_order_event_to_ai(self, order, event_type: str) -> None:
        """
        Emit order event to AI service (non-blocking).
        
        Event types: payment_success, order_shipped, order_delivered
        """
        try:
            products = [
                {
                    "product_id": str(item.product_id),
                    "product_name": item.product_name_snapshot,
                    "quantity": item.quantity,
                    "unit_price": str(item.unit_price),
                }
                for item in order.items
            ]
            
            self.ai_client.emit_order_event(
                event_type=event_type,
                user_id=order.user_id,
                order_id=order.id,
                order_number=order.order_number,
                total_items=order.total_quantity,
                order_value=order.grand_total_amount,
                products=products,
                metadata={"event_timestamp": datetime.utcnow().isoformat()},
            )
        except Exception as e:
            # Non-blocking: Log but don't fail
            logger.warning(f"Failed to emit order event to AI service: {e}")
    
    def _record_status_history(
        self,
        order_id: UUID,
        from_status: str,
        to_status: str,
        note: str = "",
    ) -> None:
        """Record status history."""
        OrderStatusHistoryModel.objects.create(
            order_id=order_id,
            from_status=from_status,
            to_status=to_status,
            note=note,
            metadata={},
        )


class HandlePaymentFailureService:
    """Handle failed payment callback."""
    
    def __init__(
        self,
        order_repo: OrderRepository = None,
        inventory_client: InventoryServiceClient = None,
    ):
        self.order_repo = order_repo or OrderRepositoryImpl()
        self.state_service = OrderStateTransitionService(self.order_repo)
        self.inventory_client = inventory_client or InventoryServiceClient()
    
    @transaction.atomic
    def execute(self, order_id: UUID, reason: str = "Payment failed") -> OrderDetailDTO:
        """
        Handle payment failure.
        
        1. Release stock reservations
        2. Update order status
        3. Record history
        """
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise ValueError(f"Order not found: {order_id}")
        
        # Release reservations
        reservation_ids = [
            ref.get("id") for ref in order.stock_reservation_refs
            if ref.get("id")
        ]
        
        if reservation_ids:
            try:
                self.inventory_client.release_reservations(
                    reservation_ids, order_id, reason
                )
            except Exception as e:
                logger.warning(f"Failed to release reservations: {e}")
        
        # Update order
        self.state_service.handle_payment_failure(order)
        
        # Record history
        self._record_status_history(
            order_id=order_id,
            from_status=order.status.value,
            to_status=OrderStatus.PAYMENT_FAILED.value,
            note=reason,
        )
        
        logger.info(f"Payment failure recorded for order {order_id}")
        
        # Return updated DTO
        order = self.order_repo.get_by_id(order_id)
        item_dtos = [order_item_to_dto(item) for item in order.items]
        return order_to_detail_dto(order, item_dtos)
    
    def _record_status_history(
        self,
        order_id: UUID,
        from_status: str,
        to_status: str,
        note: str = "",
    ) -> None:
        """Record status history."""
        OrderStatusHistoryModel.objects.create(
            order_id=order_id,
            from_status=from_status,
            to_status=to_status,
            note=note,
            metadata={},
        )


class CancelOrderService:
    """
    Cancel an order.
    
    RACE CONDITION PROTECTION:
    - Cannot cancel during AWAITING_PAYMENT (payment processing window)
    - After payment succeeds -> order becomes PAID (no cancel allowed)
    - Can only cancel PENDING or PAID orders in specific conditions
    """
    
    def __init__(
        self,
        order_repo: OrderRepository = None,
        inventory_client: InventoryServiceClient = None,
    ):
        self.order_repo = order_repo or OrderRepositoryImpl()
        self.state_service = OrderStateTransitionService(self.order_repo)
        self.inventory_client = inventory_client or InventoryServiceClient()
    
    @transaction.atomic
    def execute(self, order_id: UUID, reason: str = "User cancelled") -> OrderDetailDTO:
        """
        Cancel order with proper state machine validation.
        
        Cannot cancel if:
        - AWAITING_PAYMENT (payment processing in progress)
        - PAID or later (payment already confirmed)
        
        Can only cancel from PENDING state.
        """
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise ValueError(f"Order not found: {order_id}")
        
        # ** CRITICAL: Block cancel during payment window **
        if order.status == OrderStatus.AWAITING_PAYMENT:
            raise ValueError(
                f"Cannot cancel order {order_id}: payment is being processed. "
                f"Current status: {order.status}. "
                f"Please wait for payment callback to complete."
            )
        
        # Only allow cancellation from PENDING
        if order.status != OrderStatus.PENDING:
            raise ValueError(
                f"Cannot cancel order {order_id}: order has already been processed. "
                f"Current status: {order.status}. "
                f"Only PENDING orders can be cancelled."
            )
        
        # Release reservations if order has any (should be none for PENDING, but be defensive)
        if order.stock_reservation_refs:
            reservation_ids = [
                ref.get("id") for ref in order.stock_reservation_refs
                if ref.get("id")
            ]
            
            if reservation_ids:
                try:
                    self.inventory_client.release_reservations(
                        reservation_ids, order_id, reason
                    )
                except Exception as e:
                    logger.warning(f"Failed to release reservations: {e}")
        
        # Cancel order
        self.state_service.cancel_order(order)
        
        # Record history
        self._record_status_history(
            order_id=order_id,
            from_status=order.status.value,
            to_status=OrderStatus.CANCELLED.value,
            note=reason,
        )
        
        logger.info(f"Order {order_id} cancelled successfully from {order.status} state")
        
        # Return updated DTO
        order = self.order_repo.get_by_id(order_id)
        item_dtos = [order_item_to_dto(item) for item in order.items]
        return order_to_detail_dto(order, item_dtos)
    
    def _record_status_history(
        self,
        order_id: UUID,
        from_status: str,
        to_status: str,
        note: str = "",
    ) -> None:
        """Record status history."""
        OrderStatusHistoryModel.objects.create(
            order_id=order_id,
            from_status=from_status,
            to_status=to_status,
            note=note,
            metadata={},
        )
