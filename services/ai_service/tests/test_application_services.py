from uuid import UUID, uuid4

from modules.ai.application.services import (
    GenerateRecommendationsUseCase,
    TrackBehavioralEventUseCase,
)
from modules.ai.domain.entities import BehavioralEvent, UserPreferenceProfile
from modules.ai.domain.value_objects import BrandPreference, CategoryPreference, EventType, PriceRange, PriceRangePreference


class FakeEventRepo:
    def __init__(self):
        self.saved = None

    def add(self, event):
        self.saved = event
        return event


class FakeProfileRepo:
    def __init__(self, profile=None):
        self.profile = profile
        self.saved = None

    def get_or_create(self, user_id):
        if self.profile is None:
            self.profile = UserPreferenceProfile(id=user_id, user_id=user_id)
        return self.profile

    def save(self, profile):
        self.saved = profile
        self.profile = profile
        return profile

    def get_by_user_id(self, user_id):
        return self.profile


class FakePreferenceBuilder:
    def update_profile_with_event(self, profile, event):
        profile.purchase_intent_score += 1
        return profile


class FakeGraphService:
    def __init__(self):
        self.synced = None

    def sync_event_to_graph(self, event):
        self.synced = event


class FakePriceNormalizer:
    def normalize_price(self, amount):
        return PriceRange.UNDER_1M


class FakeScorer:
    def score_product_for_user(self, product_id, product_brand, product_category, product_price, user_profile):
        return 90.0 if product_brand.lower() == "samsung" else 10.0

    def get_reason_codes(self, product_brand, product_category, product_price, user_profile):
        return ["preferred_brand"] if product_brand.lower() == "samsung" else ["trending"]


def test_track_behavioral_event_normalizes_zero_price():
    event_repo = FakeEventRepo()
    profile_repo = FakeProfileRepo()
    graph_service = FakeGraphService()

    use_case = TrackBehavioralEventUseCase(
        event_repo=event_repo,
        profile_repo=profile_repo,
        preference_builder=FakePreferenceBuilder(),
        graph_service=graph_service,
        price_normalizer=FakePriceNormalizer(),
    )

    event = use_case.execute(
        event_type="product_click",
        user_id=uuid4(),
        price_amount=0,
        brand_name="Samsung",
        category_name="Phone",
    )

    assert event.price_range == PriceRange.UNDER_1M
    assert event_repo.saved is event
    assert graph_service.synced is event
    assert profile_repo.saved.purchase_intent_score == 1


def test_generate_recommendations_sorts_by_score():
    user_id = UUID("550e8400-e29b-41d4-a716-446655440000")
    profile = UserPreferenceProfile(
        id=user_id,
        user_id=user_id,
        preferred_brands=[BrandPreference("Samsung", 90, 3)],
        preferred_categories=[CategoryPreference("Phone", 80, 2)],
        preferred_price_ranges=[PriceRangePreference(PriceRange.FROM_5M_TO_10M, 70, 1)],
    )
    profile_repo = FakeProfileRepo(profile=profile)
    use_case = GenerateRecommendationsUseCase(profile_repo=profile_repo, scorer=FakeScorer())

    products = [
        {"id": str(uuid4()), "name": "Other", "brand": "Other", "category": "Phone", "price": 1000},
        {"id": str(uuid4()), "name": "Galaxy", "brand": "Samsung", "category": "Phone", "price": 1000},
    ]

    scored = use_case.score_products(products, user_id=user_id)

    assert scored[0]["brand"] == "Samsung"
    assert scored[0]["score"] > scored[1]["score"]
    assert scored[0]["reason_codes"] == ["preferred_brand"]
