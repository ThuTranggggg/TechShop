"""
Application Data Transfer Objects for Order context.

DTOs for API request/response serialization.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict, field
from uuid import UUID
from decimal import Decimal
from datetime import datetime


@dataclass
class OrderItemDTO:
    """DTO for order item."""
    id: UUID
    product_id: UUID
    product_name: str
    product_slug: str
    variant_id: Optional[UUID] = None
    variant_name: Optional[str] = None
    sku: Optional[str] = None
    quantity: int = 0
    unit_price: Decimal = Decimal("0")
    line_total: Decimal = Decimal("0")
    currency: str = "VND"
    brand_name: Optional[str] = None
    category_name: Optional[str] = None
    thumbnail_url: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrderTotalsDTO:
    """DTO for order totals."""
    subtotal: Decimal
    shipping_fee: Decimal = Decimal("0")
    discount: Decimal = Decimal("0")
    tax: Decimal = Decimal("0")
    grand_total: Decimal = Decimal("0")
    currency: str = "VND"


@dataclass
class AddressSnapshotDTO:
    """DTO for shipping address."""
    receiver_name: str
    receiver_phone: str
    line1: str
    line2: Optional[str] = None
    ward: Optional[str] = None
    district: str = ""
    city: str = ""
    country: str = "Vietnam"
    postal_code: Optional[str] = None


@dataclass
class OrderDetailDTO:
    """DTO for full order details."""
    id: UUID
    order_number: str
    user_id: UUID
    status: str
    payment_status: str
    fulfillment_status: str
    items: List[OrderItemDTO]
    totals: OrderTotalsDTO
    customer_name: str
    customer_email: str
    customer_phone: Optional[str]
    shipping_address: AddressSnapshotDTO
    payment_id: Optional[UUID] = None
    payment_reference: Optional[str] = None
    shipment_id: Optional[UUID] = None
    shipment_reference: Optional[str] = None
    total_quantity: int = 0
    item_count: int = 0
    notes: str = ""
    placed_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class OrderListItemDTO:
    """DTO for order list item (summary)."""
    id: UUID
    order_number: str
    status: str
    payment_status: str
    grand_total: Decimal
    currency: str
    total_quantity: int
    item_count: int
    placed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


@dataclass
class StatusHistoryItemDTO:
    """DTO for status history item."""
    from_status: Optional[str]
    to_status: str
    note: str = ""
    changed_by: Optional[UUID] = None
    created_at: Optional[datetime] = None


@dataclass
class OrderTimelineDTO:
    """DTO for order timeline."""
    order_id: UUID
    order_number: str
    status_history: List[StatusHistoryItemDTO]
    placed_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None


@dataclass
class CreateOrderFromCartRequest:
    """DTO for create order from cart request."""
    cart_id: UUID
    shipping_address: Dict[str, Any]
    notes: Optional[str] = None


@dataclass
class CreateOrderFromCheckoutPayloadRequest:
    """DTO for create order from raw checkout payload."""
    checkout_payload: Dict[str, Any]
    notes: Optional[str] = None


def order_to_detail_dto(order, items: List[OrderItemDTO]) -> OrderDetailDTO:
    """Convert domain Order to detail DTO."""
    return OrderDetailDTO(
        id=order.id,
        order_number=order.order_number.value,
        user_id=order.user_id,
        status=order.status.value,
        payment_status=order.payment_status.value,
        fulfillment_status=order.fulfillment_status.value,
        items=items,
        totals=OrderTotalsDTO(
            subtotal=order.subtotal.amount,
            shipping_fee=order.shipping_fee.amount,
            discount=order.discount.amount,
            tax=order.tax.amount,
            grand_total=order.grand_total.amount,
            currency=order.currency.value,
        ),
        customer_name=order.customer_snapshot.name,
        customer_email=order.customer_snapshot.email,
        customer_phone=order.customer_snapshot.phone,
        shipping_address=AddressSnapshotDTO(
            receiver_name=order.address_snapshot.receiver_name,
            receiver_phone=order.address_snapshot.receiver_phone,
            line1=order.address_snapshot.line1,
            line2=order.address_snapshot.line2,
            ward=order.address_snapshot.ward,
            district=order.address_snapshot.district,
            city=order.address_snapshot.city,
            country=order.address_snapshot.country,
            postal_code=order.address_snapshot.postal_code,
        ),
        payment_id=order.payment_id,
        payment_reference=order.payment_reference,
        shipment_id=order.shipment_id,
        shipment_reference=order.shipment_reference,
        total_quantity=order.total_quantity,
        item_count=order.item_count,
        notes=order.notes,
        placed_at=order.placed_at,
        paid_at=order.paid_at,
        cancelled_at=order.cancelled_at,
        completed_at=order.completed_at,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


def order_to_list_dto(order) -> OrderListItemDTO:
    """Convert domain Order to list item DTO."""
    return OrderListItemDTO(
        id=order.id,
        order_number=order.order_number.value,
        status=order.status.value,
        payment_status=order.payment_status.value,
        grand_total=order.grand_total.amount,
        currency=order.currency.value,
        total_quantity=order.total_quantity,
        item_count=order.item_count,
        placed_at=order.placed_at,
        created_at=order.created_at,
    )


def order_item_to_dto(item) -> OrderItemDTO:
    """Convert domain OrderItem to DTO."""
    return OrderItemDTO(
        id=item.id,
        product_id=item.product_snapshot.product_id,
        product_name=item.product_snapshot.name,
        product_slug=item.product_snapshot.slug,
        variant_id=item.product_reference.variant_id,
        variant_name=item.product_snapshot.variant_name,
        sku=item.product_reference.sku,
        quantity=item.quantity,
        unit_price=item.unit_price.amount,
        line_total=item.line_total.amount,
        currency=item.currency.value,
        brand_name=item.product_snapshot.brand_name,
        category_name=item.product_snapshot.category_name,
        thumbnail_url=item.product_snapshot.thumbnail_url,
        attributes=item.product_snapshot.attributes,
    )
