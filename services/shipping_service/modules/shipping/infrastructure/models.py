"""
Shipment Django ORM Models

Database models for persistence.
"""

from decimal import Decimal
from django.db import models
from django.contrib.postgres.fields import ArrayField
import json
from uuid import uuid4

from modules.shipping.domain import (
    Shipment,
    ShipmentStatus,
    ShipmentTrackingEvent,
    ShipmentTrackingEventType,
    ShipmentItemSnapshot,
    ReceiverAddress,
    ShippingProvider,
    ShippingServiceLevel,
    Money,
)


class ShipmentModel(models.Model):
    """Django model for Shipment aggregate"""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    shipment_reference = models.CharField(
        max_length=50, unique=True, db_index=True
    )
    tracking_number = models.CharField(
        max_length=50, unique=True, db_index=True
    )
    order_id = models.UUIDField(db_index=True)
    order_number = models.CharField(max_length=50, db_index=True)
    user_id = models.UUIDField(null=True, blank=True, db_index=True)
    
    # Provider & service info
    provider = models.CharField(
        max_length=20,
        choices=[(p.value, p.value) for p in ShippingProvider],
        default=ShippingProvider.MOCK.value,
    )
    service_level = models.CharField(
        max_length=20,
        choices=[(s.value, s.value) for s in ShippingServiceLevel],
        default=ShippingServiceLevel.STANDARD.value,
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.value) for s in ShipmentStatus],
        default=ShipmentStatus.CREATED.value,
        db_index=True,
    )
    
    # Tracking URLs
    tracking_url = models.TextField(null=True, blank=True)
    label_url = models.TextField(null=True, blank=True)
    
    # Package info
    package_count = models.IntegerField(default=1)
    package_weight = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    
    # Shipping cost
    shipping_fee_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(max_length=3, default="VND")
    
    # Failure info
    failure_reason = models.TextField(null=True, blank=True)
    
    # Carrier reference
    carrier_shipment_id = models.CharField(
        max_length=100, null=True, blank=True, db_index=True
    )
    
    # Timestamps for delivery lifecycle
    expected_pickup_at = models.DateTimeField(null=True, blank=True)
    expected_delivery_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Receiver address snapshot
    receiver_name = models.CharField(max_length=100)
    receiver_phone = models.CharField(max_length=20)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, null=True, blank=True)
    ward = models.CharField(max_length=100, null=True, blank=True)
    district = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default="VN")
    postal_code = models.CharField(max_length=20, null=True, blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "shipment"
        indexes = [
            models.Index(fields=["shipment_reference"]),
            models.Index(fields=["tracking_number"]),
            models.Index(fields=["order_id"]),
            models.Index(fields=["user_id"]),
            models.Index(fields=["status"]),
            models.Index(fields=["provider"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["carrier_shipment_id"]),
        ]
        verbose_name = "Shipment"
        verbose_name_plural = "Shipments"
    
    def __str__(self):
        return f"Shipment {self.shipment_reference} ({self.status})"
    
    @staticmethod
    def from_domain(shipment: Shipment) -> "ShipmentModel":
        """Convert domain Shipment to Django model"""
        return ShipmentModel(
            id=shipment.id,
            shipment_reference=shipment.shipment_reference,
            tracking_number=shipment.tracking_number,
            order_id=shipment.order_id,
            order_number=shipment.order_number,
            user_id=shipment.user_id,
            provider=shipment.provider.value,
            service_level=shipment.service_level.value,
            status=shipment.status.value,
            tracking_url=shipment.tracking_url,
            label_url=shipment.label_url,
            package_count=shipment.package_count,
            package_weight=shipment.package_weight,
            shipping_fee_amount=shipment.shipping_fee.amount if shipment.shipping_fee else None,
            currency=shipment.shipping_fee.currency if shipment.shipping_fee else "VND",
            failure_reason=shipment.failure_reason,
            carrier_shipment_id=shipment.carrier_shipment_id,
            expected_pickup_at=shipment.expected_pickup_at,
            expected_delivery_at=shipment.expected_delivery_at,
            shipped_at=shipment.shipped_at,
            delivered_at=shipment.delivered_at,
            cancelled_at=shipment.cancelled_at,
            receiver_name=shipment.receiver_address.name,
            receiver_phone=shipment.receiver_address.phone,
            address_line1=shipment.receiver_address.address_line1,
            address_line2=shipment.receiver_address.address_line2,
            ward=shipment.receiver_address.ward,
            district=shipment.receiver_address.district,
            city=shipment.receiver_address.city,
            country=shipment.receiver_address.country,
            postal_code=shipment.receiver_address.postal_code,
            metadata=shipment.metadata,
            created_at=shipment.created_at,
            updated_at=shipment.updated_at,
        )
    
    def to_domain(self) -> Shipment:
        """Convert Django model to domain Shipment"""
        receiver_address = ReceiverAddress(
            name=self.receiver_name,
            phone=self.receiver_phone,
            address_line1=self.address_line1,
            address_line2=self.address_line2,
            ward=self.ward,
            district=self.district,
            city=self.city,
            country=self.country,
            postal_code=self.postal_code,
        )
        
        shipping_fee = None
        if self.shipping_fee_amount is not None:
            shipping_fee = Money(
                amount=self.shipping_fee_amount,
                currency=self.currency,
            )
        
        # Get items
        items = [
            item.to_domain()
            for item in self.items.all()
        ]
        
        shipment = Shipment(
            id=self.id,
            order_id=self.order_id,
            order_number=self.order_number,
            user_id=self.user_id,
            shipment_reference=self.shipment_reference,
            tracking_number=self.tracking_number,
            receiver_address=receiver_address,
            items=items,
            provider=ShippingProvider(self.provider),
            service_level=ShippingServiceLevel(self.service_level),
            status=ShipmentStatus(self.status),
            tracking_url=self.tracking_url,
            label_url=self.label_url,
            package_count=self.package_count,
            package_weight=self.package_weight,
            shipping_fee=shipping_fee,
            failure_reason=self.failure_reason,
            carrier_shipment_id=self.carrier_shipment_id,
            expected_pickup_at=self.expected_pickup_at,
            expected_delivery_at=self.expected_delivery_at,
            shipped_at=self.shipped_at,
            delivered_at=self.delivered_at,
            cancelled_at=self.cancelled_at,
            created_at=self.created_at,
            updated_at=self.updated_at,
            metadata=self.metadata,
        )
        
        # Add tracking events
        for event_model in self.tracking_events.all():
            shipment.tracking_events.append(event_model.to_domain())
        
        return shipment


class ShipmentItemModel(models.Model):
    """Django model for ShipmentItem"""
    
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    shipment = models.ForeignKey(
        ShipmentModel,
        on_delete=models.CASCADE,
        related_name="items",
    )
    order_item_id = models.UUIDField(null=True, blank=True, db_index=True)
    product_id = models.UUIDField(db_index=True)
    variant_id = models.UUIDField(null=True, blank=True, db_index=True)
    sku = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    quantity = models.IntegerField(default=1)
    product_name_snapshot = models.CharField(max_length=255)
    variant_name_snapshot = models.CharField(max_length=255, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "shipment_item"
        indexes = [
            models.Index(fields=["shipment_id"]),
            models.Index(fields=["product_id"]),
            models.Index(fields=["sku"]),
        ]
        verbose_name = "Shipment Item"
        verbose_name_plural = "Shipment Items"
    
    def __str__(self):
        return f"{self.product_name_snapshot} x{self.quantity}"
    
    @staticmethod
    def from_domain(shipment_id, item: ShipmentItemSnapshot) -> "ShipmentItemModel":
        """Convert domain item to Django model"""
        return ShipmentItemModel(
            shipment_id=shipment_id,
            order_item_id=item.order_item_id,
            product_id=item.product_id,
            variant_id=item.variant_id,
            sku=item.sku,
            quantity=item.quantity,
            product_name_snapshot=item.product_name_snapshot,
            variant_name_snapshot=item.variant_name_snapshot,
        )
    
    def to_domain(self) -> ShipmentItemSnapshot:
        """Convert Django model to domain item"""
        return ShipmentItemSnapshot(
            order_item_id=self.order_item_id,
            product_id=self.product_id,
            variant_id=self.variant_id,
            sku=self.sku,
            quantity=self.quantity,
            product_name_snapshot=self.product_name_snapshot,
            variant_name_snapshot=self.variant_name_snapshot,
        )


class ShipmentTrackingEventModel(models.Model):
    """Django model for ShipmentTrackingEvent"""
    
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    shipment = models.ForeignKey(
        ShipmentModel,
        on_delete=models.CASCADE,
        related_name="tracking_events",
    )
    event_type = models.CharField(
        max_length=30,
        choices=[(e.value, e.value) for e in ShipmentTrackingEventType],
    )
    status_before = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=[(s.value, s.value) for s in ShipmentStatus],
    )
    status_after = models.CharField(
        max_length=20,
        choices=[(s.value, s.value) for s in ShipmentStatus],
    )
    description = models.TextField(null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    provider_event_id = models.CharField(
        max_length=100, null=True, blank=True, db_index=True
    )
    raw_payload = models.JSONField(default=dict)
    event_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = "shipment_tracking_event"
        indexes = [
            models.Index(fields=["shipment_id"]),
            models.Index(fields=["event_type"]),
            models.Index(fields=["provider_event_id"]),
            models.Index(fields=["created_at"]),
        ]
        verbose_name = "Shipment Tracking Event"
        verbose_name_plural = "Shipment Tracking Events"
        ordering = ["created_at"]
    
    def __str__(self):
        return f"{self.event_type} on {self.created_at}"
    
    @staticmethod
    def from_domain(event: ShipmentTrackingEvent) -> "ShipmentTrackingEventModel":
        """Convert domain event to Django model"""
        return ShipmentTrackingEventModel(
            id=event.id,
            shipment_id=event.shipment_id,
            event_type=event.event_type.value,
            status_before=event.status_before.value if event.status_before else None,
            status_after=event.status_after.value,
            description=event.description,
            location=event.location,
            provider_event_id=event.provider_event_id,
            raw_payload=event.raw_payload,
            event_time=event.event_time,
            created_at=event.created_at,
        )
    
    def to_domain(self) -> ShipmentTrackingEvent:
        """Convert Django model to domain event"""
        return ShipmentTrackingEvent(
            id=self.id,
            shipment_id=self.shipment_id,
            event_type=ShipmentTrackingEventType(self.event_type),
            status_before=ShipmentStatus(self.status_before) if self.status_before else None,
            status_after=ShipmentStatus(self.status_after),
            description=self.description,
            location=self.location,
            provider_event_id=self.provider_event_id,
            raw_payload=self.raw_payload,
            event_time=self.event_time,
            created_at=self.created_at,
        )
