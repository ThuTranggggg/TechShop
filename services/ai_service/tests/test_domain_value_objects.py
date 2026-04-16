from decimal import Decimal

import pytest

from modules.ai.domain.value_objects import BrandPreference, Money, PriceRange


def test_money_rejects_negative_amount():
    with pytest.raises(ValueError, match="Amount cannot be negative"):
        Money(amount=Decimal("-1"))


def test_brand_preference_rejects_out_of_range_score():
    with pytest.raises(ValueError, match="Score must be between 0 and 100"):
        BrandPreference(brand_name="Samsung", score=101, interaction_count=1)


def test_price_range_enum_contains_expected_bucket():
    assert PriceRange.FROM_5M_TO_10M.value == "from_5m_to_10m"
