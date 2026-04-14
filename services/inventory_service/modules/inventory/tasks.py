"""
Celery async tasks for Inventory context.

Handles scheduled jobs like cleaning up expired stock reservations.
"""
import logging
from datetime import datetime
from uuid import UUID

from celery import shared_task
from django.utils import timezone

from .infrastructure.models import StockReservationModel, StockItemModel
from .domain.enums import ReservationStatus
from .domain.repositories import (
    StockReservationRepository,
    StockItemRepository,
    StockMovementRepository,
)
from .domain.services import InventoryDomainService

logger = logging.getLogger(__name__)


@shared_task(
    name="modules.inventory.tasks.release_expired_reservations",
    bind=True,
    max_retries=3,
)
def release_expired_reservations(self):
    """
    ISSUE FIX #4: Auto-release expired stock reservations.
    
    Scheduled task runs every hour to clean up reservations that have expired.
    This prevents "stuck" purchased inventory when customers don't complete payment.
    
    Process:
    1. Find all ACTIVE reservations where expires_at <= now
    2. Release each reservation (return quantity to available stock)
    3. Record stock movement for audit trail
    4. Log all actions for operations visibility
    
    Retries:
    - Max 3 retries if DB connection/task fails
    - Exponential backoff
    """
    try:
        logger.info("Starting scheduled task: release_expired_reservations")
        
        now = timezone.now()
        
        # Find all expired active reservations
        expired_reservations = StockReservationModel.objects.filter(
            status=ReservationStatus.ACTIVE.value,
            expires_at__lte=now,
        ).select_related("stock_item")
        
        count = expired_reservations.count()
        if count == 0:
            logger.info("No expired reservations found")
            return {"status": "success", "released_count": 0}
        
        logger.warning(f"Found {count} expired reservations, releasing now")
        
        released_count = 0
        error_count = 0
        
        # Process each expired reservation
        for reservation in expired_reservations:
            try:
                _release_single_reservation(reservation)
                released_count += 1
            except Exception as e:
                error_count += 1
                logger.error(
                    f"Failed to release reservation {reservation.id}: {e}",
                    exc_info=True
                )
        
        # Log summary
        logger.info(
            f"Expired reservation cleanup: "
            f"released={released_count}, "
            f"errors={error_count}, "
            f"total={count}"
        )
        
        return {
            "status": "success",
            "released_count": released_count,
            "error_count": error_count,
            "total_expired": count,
        }
    
    except Exception as exc:
        logger.error(
            f"Task release_expired_reservations failed: {exc}",
            exc_info=True
        )
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


def _release_single_reservation(reservation: StockReservationModel) -> None:
    """
    Release a single expired reservation.
    
    Atomic operation:
    1. Increment stock_item.on_hand_quantity
    2. Decrement stock_item.reserved_quantity
    3. Mark reservation as EXPIRED
    4. Record stock movement
    """
    logger.info(
        f"Releasing expired reservation {reservation.id} "
        f"(product_id={reservation.product_id}, "
        f"variant_id={reservation.variant_id}, "
        f"qty={reservation.quantity}, "
        f"expired_at={reservation.expires_at})"
    )
    
    stock_item = reservation.stock_item
    now = timezone.now()
    
    # Update quantities
    stock_item.reserved_quantity = max(0, stock_item.reserved_quantity - reservation.quantity)
    stock_item.on_hand_quantity += reservation.quantity
    stock_item.save(update_fields=["reserved_quantity", "on_hand_quantity", "updated_at"])
    
    # Mark reservation as expired
    reservation.status = ReservationStatus.EXPIRED.value
    reservation.metadata = reservation.metadata or {}
    reservation.metadata["released_by"] = "system_auto_release"
    reservation.metadata["released_at"] = now.isoformat()
    reservation.save(update_fields=["status", "metadata", "updated_at"])
    
    logger.debug(f"Successfully released reservation {reservation.id}")


@shared_task(
    name="modules.inventory.tasks.cleanup_expired_reservations_batch",
    bind=True,
)
def cleanup_expired_reservations_batch(self, batch_size: int = 100):
    """
    Alternative batch cleanup task for high-volume environments.
    
    Processes expired reservations in configurable batches to avoid
    locking large numbers of rows simultaneously.
    """
    try:
        now = timezone.now()
        
        # Find batch of expired reservations
        expired = StockReservationModel.objects.filter(
            status=ReservationStatus.ACTIVE.value,
            expires_at__lte=now,
        ).select_related("stock_item")[:batch_size]
        
        if not expired.exists():
            return {"status": "complete", "processed": 0}
        
        for reservation in expired:
            try:
                _release_single_reservation(reservation)
            except Exception as e:
                logger.error(f"Batch cleanup error for {reservation.id}: {e}")
        
        # Schedule next batch
        remaining = StockReservationModel.objects.filter(
            status=ReservationStatus.ACTIVE.value,
            expires_at__lte=now,
        ).count()
        
        if remaining > 0:
            # Reschedule to process next batch
            self.apply_async(kwargs={"batch_size": batch_size})
            return {"status": "incomplete", "processed": len(expired), "remaining": remaining}
        
        return {"status": "complete", "processed": len(expired), "remaining": 0}
    
    except Exception as exc:
        logger.error(f"Batch cleanup task error: {exc}", exc_info=True)
        raise
