"""
Shipment Application Services

Use case services orchestrating domain logic.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple
from uuid import UUID, uuid4

from django.db import transaction

from modules.shipping.domain import (
    Shipment,
    ShipmentFactory,
    ShipmentStatus,
    ShipmentStateService,
    ShipmentValidator,
    ShipmentItemSnapshot,
    ReceiverAddress,
    ShippingProvider,
    ShippingServiceLevel,
    Money,
)
from modules.shipping.infrastructure import (
    ShipmentRepositoryImpl,
    ShipmentTrackingEventRepositoryImpl,
    ShippingProviderFactory,
    OrderServiceClient,
)
from .dtos import (
    CreateShipmentRequestDTO,
    ShipmentDetailDTO,
    ShipmentStatusDTO,
    ShipmentTrackingResponseDTO,
    shipment_to_detail_dto,
    shipment_to_status_dto,
    shipment_to_tracking_response_dto,
)

logger = logging.getLogger(__name__)


class CreateShipmentService:
    """Use case: Create shipment for order"""

    def __init__(
        self,
        shipment_repo: Optional[object] = None,
        provider_factory: Optional[object] = None,
        order_client: Optional[object] = None,
    ):
        self.shipment_repo = shipment_repo or ShipmentRepositoryImpl()
        self.provider_factory = provider_factory or ShippingProviderFactory()
        self.event_repo = ShipmentTrackingEventRepositoryImpl()
        self.order_client = order_client or OrderServiceClient()

    @transaction.atomic
    def execute(self, request: CreateShipmentRequestDTO) -> Tuple[bool, Optional[str], Optional[ShipmentDetailDTO]]:
        """Create shipment"""
        try:
            # Validate receiver address
            receiver_address = ReceiverAddress(
                name=request.receiver_name,
                phone=request.receiver_phone,
                address_line1=request.address_line1,
                address_line2=request.address_line2,
                ward=request.ward,
                district=request.district,
                city=request.city,
                country=request.country,
                postal_code=request.postal_code,
            )

            is_valid, error = ShipmentValidator.validate_receiver_address(receiver_address)
            if not is_valid:
                return False, error, None

            # Parse items
            items = []
            if request.items:
                for item_data in request.items:
                    item = ShipmentItemSnapshot(
                        order_item_id=item_data.get("order_item_id"),
                        product_id=item_data.get("product_id"),
                        variant_id=item_data.get("variant_id"),
                        sku=item_data.get("sku"),
                        quantity=int(item_data.get("quantity", 1)),
                        product_name_snapshot=item_data.get("product_name_snapshot", ""),
                        variant_name_snapshot=item_data.get("variant_name_snapshot"),
                    )
                    items.append(item)

            is_valid, error = ShipmentValidator.validate_shipment_items(items)
            if not is_valid:
                return False, error, None

            # Check for existing active shipment
            existing = self.shipment_repo.get_by_order(request.order_id)
            if existing and existing.is_active():
                return False, "Order already has an active shipment", None

            # Create shipment reference & tracking number
            shipment_reference = f"SHIP-{uuid4().hex[:8].upper()}"
            tracking_number = f"TRK-{uuid4().hex[:12].upper()}"

            # Create Money object
            shipping_fee = None
            if request.shipping_fee_amount:
                shipping_fee = Money(
                    amount=request.shipping_fee_amount,
                    currency=request.currency,
                )

            # Create domain shipment
            shipment = ShipmentFactory.create_shipment(
                order_id=request.order_id,
                order_number=request.order_number,
                user_id=request.user_id,
                shipment_reference=shipment_reference,
                tracking_number=tracking_number,
                receiver_address=receiver_address,
                items=items,
                provider=ShippingProvider(request.provider),
                service_level=ShippingServiceLevel(request.service_level),
                expected_delivery_at=datetime.utcnow() + timedelta(days=3),
                shipping_fee=shipping_fee,
            )

            # Call provider to create shipment
            provider = self.provider_factory.get_provider(request.provider)
            provider_response = provider.create_shipment(shipment)

            if not provider_response.success:
                logger.error(f"Provider create failed: {provider_response.message}")
                return False, f"Provider error: {provider_response.message}", None

            # Update shipment with provider info
            if provider_response.carrier_shipment_id:
                shipment.carrier_shipment_id = provider_response.carrier_shipment_id
            if provider_response.tracking_url:
                shipment.tracking_url = provider_response.tracking_url
            if provider_response.expected_delivery_at:
                shipment.expected_delivery_at = provider_response.expected_delivery_at

            # Transition to pending pickup
            try:
                ShipmentStateService.transition_to_pending_pickup(shipment)
            except ValueError:
                pass  # Already in right status

            # Save shipment
            shipment = self.shipment_repo.save(shipment)

            # Notify order_service
            self.order_client.notify_shipment_created(
                order_id=shipment.order_id,
                shipment_id=shipment.id,
                shipment_reference=shipment.shipment_reference,
                tracking_number=shipment.tracking_number,
                tracking_url=shipment.tracking_url,
            )

            # Return DTO
            dto = shipment_to_detail_dto(shipment)
            return True, None, dto

        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            return False, str(e), None
        except Exception as e:
            logger.error(f"Error creating shipment: {str(e)}")
            return False, "Internal server error", None


class GetShipmentDetailService:
    """Use case: Get shipment detail"""

    def __init__(self, shipment_repo: Optional[object] = None):
        self.shipment_repo = shipment_repo or ShipmentRepositoryImpl()

    def execute(self, shipment_id: str) -> Optional[ShipmentDetailDTO]:
        """Get shipment by ID"""
        try:
            shipment = self.shipment_repo.get_by_id(UUID(shipment_id))
            if not shipment:
                return None
            return shipment_to_detail_dto(shipment)
        except Exception as e:
            logger.error(f"Error getting shipment: {str(e)}")
            return None


class GetShipmentByReferenceService:
    """Use case: Get shipment by reference"""

    def __init__(self, shipment_repo: Optional[object] = None):
        self.shipment_repo = shipment_repo or ShipmentRepositoryImpl()

    def execute(self, shipment_reference: str) -> Optional[ShipmentDetailDTO]:
        """Get shipment by reference"""
        try:
            shipment = self.shipment_repo.get_by_reference(shipment_reference)
            if not shipment:
                return None
            return shipment_to_detail_dto(shipment)
        except Exception as e:
            logger.error(f"Error getting shipment: {str(e)}")
            return None


class GetShipmentStatusService:
    """Use case: Get quick shipment status"""

    def __init__(self, shipment_repo: Optional[object] = None):
        self.shipment_repo = shipment_repo or ShipmentRepositoryImpl()

    def execute(self, shipment_reference: str) -> Optional[ShipmentStatusDTO]:
        """Get shipment status"""
        try:
            shipment = self.shipment_repo.get_by_reference(shipment_reference)
            if not shipment:
                return None
            return shipment_to_status_dto(shipment)
        except Exception as e:
            logger.error(f"Error getting shipment status: {str(e)}")
            return None


class GetShipmentTrackingService:
    """Use case: Get public shipment tracking"""

    def __init__(self, shipment_repo: Optional[object] = None):
        self.shipment_repo = shipment_repo or ShipmentRepositoryImpl()

    def execute(self, shipment_reference: str) -> Optional[ShipmentTrackingResponseDTO]:
        """Get shipment tracking info"""
        try:
            shipment = self.shipment_repo.get_by_reference(shipment_reference)
            if not shipment:
                return None
            return shipment_to_tracking_response_dto(shipment)
        except Exception as e:
            logger.error(f"Error getting shipment tracking: {str(e)}")
            return None


class GetShipmentByOrderService:
    """Use case: Get shipment for order"""

    def __init__(self, shipment_repo: Optional[object] = None):
        self.shipment_repo = shipment_repo or ShipmentRepositoryImpl()

    def execute(self, order_id: str) -> Optional[ShipmentDetailDTO]:
        """Get shipment for order"""
        try:
            shipment = self.shipment_repo.get_by_order(UUID(order_id))
            if not shipment:
                return None
            return shipment_to_detail_dto(shipment)
        except Exception as e:
            logger.error(f"Error getting shipment for order: {str(e)}")
            return None


class MarkPickedUpService:
    """Use case: Mark shipment as picked up"""

    def __init__(
        self,
        shipment_repo: Optional[object] = None,
        order_client: Optional[object] = None,
    ):
        self.shipment_repo = shipment_repo or ShipmentRepositoryImpl()
        self.order_client = order_client or OrderServiceClient()

    @transaction.atomic
    def execute(self, shipment_reference: str) -> Tuple[bool, Optional[str], Optional[ShipmentDetailDTO]]:
        """Mark shipment as picked up"""
        try:
            shipment = self.shipment_repo.get_by_reference(shipment_reference)
            if not shipment:
                return False, "Shipment not found", None

            ShipmentStateService.mark_picked_up(shipment)
            shipment = self.shipment_repo.save(shipment)

            # Notify order_service
            self.order_client.notify_shipment_status_updated(
                order_id=shipment.order_id,
                shipment_id=shipment.id,
                shipment_reference=shipment.shipment_reference,
                status=shipment.status.value,
            )

            return True, None, shipment_to_detail_dto(shipment)
        except ValueError as e:
            return False, str(e), None
        except Exception as e:
            logger.error(f"Error marking picked up: {str(e)}")
            return False, "Internal server error", None


class MarkInTransitService:
    """Use case: Mark shipment as in transit"""

    def __init__(
        self,
        shipment_repo: Optional[object] = None,
        order_client: Optional[object] = None,
    ):
        self.shipment_repo = shipment_repo or ShipmentRepositoryImpl()
        self.order_client = order_client or OrderServiceClient()

    @transaction.atomic
    def execute(
        self,
        shipment_reference: str,
        location: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Optional[ShipmentDetailDTO]]:
        """Mark shipment as in transit"""
        try:
            shipment = self.shipment_repo.get_by_reference(shipment_reference)
            if not shipment:
                return False, "Shipment not found", None

            ShipmentStateService.mark_in_transit(shipment, location=location)
            shipment = self.shipment_repo.save(shipment)

            self.order_client.notify_shipment_status_updated(
                order_id=shipment.order_id,
                shipment_id=shipment.id,
                shipment_reference=shipment.shipment_reference,
                status=shipment.status.value,
                location=location,
            )

            return True, None, shipment_to_detail_dto(shipment)
        except ValueError as e:
            return False, str(e), None
        except Exception as e:
            logger.error(f"Error marking in transit: {str(e)}")
            return False, "Internal server error", None


class MarkOutForDeliveryService:
    """Use case: Mark shipment as out for delivery"""

    def __init__(
        self,
        shipment_repo: Optional[object] = None,
        order_client: Optional[object] = None,
    ):
        self.shipment_repo = shipment_repo or ShipmentRepositoryImpl()
        self.order_client = order_client or OrderServiceClient()

    @transaction.atomic
    def execute(
        self,
        shipment_reference: str,
        location: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Optional[ShipmentDetailDTO]]:
        """Mark shipment as out for delivery"""
        try:
            shipment = self.shipment_repo.get_by_reference(shipment_reference)
            if not shipment:
                return False, "Shipment not found", None

            ShipmentStateService.mark_out_for_delivery(shipment, location=location)
            shipment = self.shipment_repo.save(shipment)

            self.order_client.notify_shipment_status_updated(
                order_id=shipment.order_id,
                shipment_id=shipment.id,
                shipment_reference=shipment.shipment_reference,
                status=shipment.status.value,
                location=location,
            )

            return True, None, shipment_to_detail_dto(shipment)
        except ValueError as e:
            return False, str(e), None
        except Exception as e:
            logger.error(f"Error marking out for delivery: {str(e)}")
            return False, "Internal server error", None


class MarkDeliveredService:
    """Use case: Mark shipment as delivered"""

    def __init__(
        self,
        shipment_repo: Optional[object] = None,
        order_client: Optional[object] = None,
    ):
        self.shipment_repo = shipment_repo or ShipmentRepositoryImpl()
        self.order_client = order_client or OrderServiceClient()

    @transaction.atomic
    def execute(
        self,
        shipment_reference: str,
        location: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Optional[ShipmentDetailDTO]]:
        """Mark shipment as delivered"""
        try:
            shipment = self.shipment_repo.get_by_reference(shipment_reference)
            if not shipment:
                return False, "Shipment not found", None

            # Check if already delivered (idempotency)
            if shipment.status == ShipmentStatus.DELIVERED:
                return True, None, shipment_to_detail_dto(shipment)

            ShipmentStateService.mark_delivered(shipment, location=location)
            shipment = self.shipment_repo.save(shipment)

            # Notify order_service
            self.order_client.notify_shipment_delivered(
                order_id=shipment.order_id,
                shipment_id=shipment.id,
                shipment_reference=shipment.shipment_reference,
                delivered_at=shipment.delivered_at.isoformat(),
            )

            return True, None, shipment_to_detail_dto(shipment)
        except ValueError as e:
            return False, str(e), None
        except Exception as e:
            logger.error(f"Error marking delivered: {str(e)}")
            return False, "Internal server error", None


class MarkFailedDeliveryService:
    """Use case: Mark delivery as failed"""

    def __init__(
        self,
        shipment_repo: Optional[object] = None,
        order_client: Optional[object] = None,
    ):
        self.shipment_repo = shipment_repo or ShipmentRepositoryImpl()
        self.order_client = order_client or OrderServiceClient()

    @transaction.atomic
    def execute(
        self,
        shipment_reference: str,
        failure_reason: str,
        location: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Optional[ShipmentDetailDTO]]:
        """Mark delivery as failed"""
        try:
            shipment = self.shipment_repo.get_by_reference(shipment_reference)
            if not shipment:
                return False, "Shipment not found", None

            ShipmentStateService.mark_failed_delivery(
                shipment,
                reason=failure_reason,
                location=location,
            )
            shipment = self.shipment_repo.save(shipment)

            # Notify order_service
            self.order_client.notify_shipment_failed(
                order_id=shipment.order_id,
                shipment_id=shipment.id,
                shipment_reference=shipment.shipment_reference,
                failure_reason=failure_reason,
            )

            return True, None, shipment_to_detail_dto(shipment)
        except ValueError as e:
            return False, str(e), None
        except Exception as e:
            logger.error(f"Error marking failed delivery: {str(e)}")
            return False, "Internal server error", None


class CancelShipmentService:
    """Use case: Cancel shipment"""

    def __init__(
        self,
        shipment_repo: Optional[object] = None,
        order_client: Optional[object] = None,
    ):
        self.shipment_repo = shipment_repo or ShipmentRepositoryImpl()
        self.order_client = order_client or OrderServiceClient()

    @transaction.atomic
    def execute(
        self,
        shipment_reference: str,
        reason: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Optional[ShipmentDetailDTO]]:
        """Cancel shipment"""
        try:
            shipment = self.shipment_repo.get_by_reference(shipment_reference)
            if not shipment:
                return False, "Shipment not found", None

            ShipmentStateService.cancel(shipment, reason=reason)
            shipment = self.shipment_repo.save(shipment)

            self.order_client.notify_shipment_status_updated(
                order_id=shipment.order_id,
                shipment_id=shipment.id,
                shipment_reference=shipment.shipment_reference,
                status=shipment.status.value,
            )

            return True, None, shipment_to_detail_dto(shipment)
        except Exception as e:
            logger.error(f"Error cancelling shipment: {str(e)}")
            return False, str(e), None


class MockAdvanceShipmentStatusService:
    """Use case: Mock shipment progression (for development)"""

    def __init__(
        self,
        shipment_repo: Optional[object] = None,
        provider_factory: Optional[object] = None,
        order_client: Optional[object] = None,
    ):
        self.shipment_repo = shipment_repo or ShipmentRepositoryImpl()
        self.provider_factory = provider_factory or ShippingProviderFactory()
        self.order_client = order_client or OrderServiceClient()

    @transaction.atomic
    def execute(
        self,
        shipment_reference: str,
        target_status: str,
    ) -> Tuple[bool, Optional[str], Optional[ShipmentDetailDTO]]:
        """Advance mock shipment to target status"""
        try:
            shipment = self.shipment_repo.get_by_reference(shipment_reference)
            if not shipment:
                return False, "Shipment not found", None

            # Parse target status
            try:
                target = ShipmentStatus(target_status)
            except ValueError:
                return False, f"Invalid status: {target_status}", None

            # Validate transition
            if not shipment.can_transition_to(target):
                return False, f"Cannot transition to {target_status}", None

            # Apply transitions step by step to populate events properly
            status_path = self._get_status_path(shipment.status, target)
            for status in status_path:
                if status == ShipmentStatus.PICKED_UP:
                    ShipmentStateService.mark_picked_up(shipment)
                elif status == ShipmentStatus.IN_TRANSIT:
                    ShipmentStateService.mark_in_transit(shipment)
                elif status == ShipmentStatus.OUT_FOR_DELIVERY:
                    ShipmentStateService.mark_out_for_delivery(shipment)
                elif status == ShipmentStatus.DELIVERED:
                    ShipmentStateService.mark_delivered(shipment)

            shipment = self.shipment_repo.save(shipment)

            # Notify order_service
            self.order_client.notify_shipment_status_updated(
                order_id=shipment.order_id,
                shipment_id=shipment.id,
                shipment_reference=shipment.shipment_reference,
                status=shipment.status.value,
            )

            return True, None, shipment_to_detail_dto(shipment)
        except Exception as e:
            logger.error(f"Error advancing mock status: {str(e)}")
            return False, str(e), None

    @staticmethod
    def _get_status_path(current: ShipmentStatus, target: ShipmentStatus) -> List[ShipmentStatus]:
        """Get path of statuses to transition through"""
        path_map = {
            (ShipmentStatus.CREATED, ShipmentStatus.PENDING_PICKUP): [ShipmentStatus.PENDING_PICKUP],
            (ShipmentStatus.PENDING_PICKUP, ShipmentStatus.PICKED_UP): [ShipmentStatus.PICKED_UP],
            (ShipmentStatus.PICKED_UP, ShipmentStatus.IN_TRANSIT): [ShipmentStatus.IN_TRANSIT],
            (ShipmentStatus.IN_TRANSIT, ShipmentStatus.OUT_FOR_DELIVERY): [ShipmentStatus.OUT_FOR_DELIVERY],
            (ShipmentStatus.OUT_FOR_DELIVERY, ShipmentStatus.DELIVERED): [ShipmentStatus.DELIVERED],
            (ShipmentStatus.CREATED, ShipmentStatus.DELIVERED): [
                ShipmentStatus.PENDING_PICKUP,
                ShipmentStatus.PICKED_UP,
                ShipmentStatus.IN_TRANSIT,
                ShipmentStatus.OUT_FOR_DELIVERY,
                ShipmentStatus.DELIVERED,
            ],
        }
        return path_map.get((current, target), [target])
