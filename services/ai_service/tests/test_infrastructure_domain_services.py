from uuid import uuid4

from modules.ai.domain.entities import BehavioralEvent, UserPreferenceProfile
from modules.ai.domain.value_objects import EventType, PriceRange
from modules.ai.infrastructure.domain_services import DefaultPriceRangeNormalizer, EventBasedPreferenceProfileBuilder


def test_price_range_normalizer_uses_expected_buckets():
    normalizer = DefaultPriceRangeNormalizer()

    assert normalizer.normalize_price(0) == PriceRange.UNDER_1M
    assert normalizer.normalize_price(1_000_000) == PriceRange.FROM_1M_TO_3M
    assert normalizer.normalize_price(20_000_000) == PriceRange.ABOVE_20M


def test_preference_profile_builder_tracks_brand_category_and_keywords():
    builder = EventBasedPreferenceProfileBuilder(price_normalizer=DefaultPriceRangeNormalizer())
    profile = UserPreferenceProfile(id=uuid4(), user_id=uuid4())
    event = BehavioralEvent(
        id=uuid4(),
        event_type=EventType.ADD_TO_CART,
        brand_name="Samsung",
        category_name="Phone",
        price_amount=7_000_000,
        keyword="galaxy",
    )

    updated = builder.update_profile_with_event(profile, event)

    assert updated.preferred_brands[0].brand_name == "Samsung"
    assert updated.preferred_categories[0].category_name == "Phone"
    assert updated.preferred_price_ranges[0].price_range == PriceRange.FROM_5M_TO_10M
    assert updated.recent_keywords == ["galaxy"]
