from decimal import Decimal
from uuid import uuid4

from modules.ai.domain.value_objects import EventType, PriceRange
from modules.ai.infrastructure.models import BehavioralEventModel
from modules.ai.infrastructure.repositories import DjangoBehavioralEventRepository


def test_behavioral_event_repository_preserves_zero_price_amount():
    model = BehavioralEventModel(
        id=uuid4(),
        event_type=EventType.PRODUCT_VIEW.value,
        user_id=uuid4(),
        product_id=uuid4(),
        price_amount=Decimal("0.00"),
        price_range=PriceRange.UNDER_1M.value,
        occurred_at="2026-01-01T00:00:00Z",
    )

    event = DjangoBehavioralEventRepository._model_to_entity(model)

    assert event.price_amount == 0.0
    assert event.price_range == PriceRange.UNDER_1M
