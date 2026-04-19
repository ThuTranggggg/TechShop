"""
Presentation layer - Serializers for API validation and serialization.
"""
from rest_framework import serializers
from typing import Optional, Dict, Any, List


class BehavioralEventSerializer(serializers.Serializer):
    """Serializer for behavioral events."""

    event_type = serializers.ChoiceField(
        choices=[
            "search",
            "product_view",
            "product_click",
            "view_category",
            "add_to_cart",
            "remove_from_cart",
            "add_to_wishlist",
            "checkout_started",
            "order_created",
            "order_cancel",
            "payment_success",
            "chat_query",
        ]
    )
    user_id = serializers.UUIDField(required=False, allow_null=True)
    session_id = serializers.CharField(required=False, allow_blank=True, max_length=100)
    product_id = serializers.UUIDField(required=False, allow_null=True)
    variant_id = serializers.UUIDField(required=False, allow_null=True)
    brand_name = serializers.CharField(required=False, allow_blank=True, max_length=100)
    category_name = serializers.CharField(required=False, allow_blank=True, max_length=100)
    price_amount = serializers.DecimalField(
        required=False,
        allow_null=True,
        max_digits=12,
        decimal_places=2,
    )
    keyword = serializers.CharField(required=False, allow_blank=True, max_length=255)
    source_service = serializers.CharField(required=False, allow_blank=True, max_length=50)
    occurred_at = serializers.DateTimeField(required=False, allow_null=True)
    metadata = serializers.JSONField(required=False, allow_null=True)


class BulkBehavioralEventSerializer(serializers.Serializer):
    """Serializer for bulk event ingestion."""

    events = BehavioralEventSerializer(many=True)

    def validate_events(self, value):
        if not value:
            raise serializers.ValidationError("Events list cannot be empty")
        if len(value) > 1000:
            raise serializers.ValidationError("Maximum 1000 events per request")
        return value


class BrandPreferenceSerializer(serializers.Serializer):
    """Serializer for brand preferences."""

    brand_name = serializers.CharField()
    score = serializers.FloatField(min_value=0)
    interaction_count = serializers.IntegerField(min_value=0, required=False)
    count = serializers.IntegerField(min_value=0, required=False)


class CategoryPreferenceSerializer(serializers.Serializer):
    """Serializer for category preferences."""

    category_name = serializers.CharField()
    score = serializers.FloatField(min_value=0)
    interaction_count = serializers.IntegerField(min_value=0, required=False)
    count = serializers.IntegerField(min_value=0, required=False)


class PriceRangePreferenceSerializer(serializers.Serializer):
    """Serializer for price range preferences."""

    price_range = serializers.CharField()
    score = serializers.FloatField(min_value=0)
    interaction_count = serializers.IntegerField(min_value=0, required=False)
    count = serializers.IntegerField(min_value=0, required=False)


class UserPreferenceSummarySerializer(serializers.Serializer):
    """Serializer for user preference summary."""

    user_id = serializers.CharField()
    top_brands = BrandPreferenceSerializer(many=True)
    top_categories = CategoryPreferenceSerializer(many=True)
    top_price_ranges = PriceRangePreferenceSerializer(many=True)
    recent_keywords = serializers.ListField(child=serializers.CharField())
    purchase_intent_score = serializers.FloatField()
    last_interaction_at = serializers.DateTimeField(allow_null=True)
    graph_top_brands = BrandPreferenceSerializer(many=True, required=False)
    graph_top_categories = CategoryPreferenceSerializer(many=True, required=False)


class ProductSerializer(serializers.Serializer):
    """Serializer for products in recommendations."""

    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField(required=False)
    brand = serializers.CharField()
    category = serializers.CharField()
    price = serializers.DecimalField(max_digits=12, decimal_places=2)
    thumbnail_url = serializers.URLField(required=False)
    stock_available = serializers.BooleanField(required=False, default=True)


class RecommendationSerializer(serializers.Serializer):
    """Serializer for recommendations."""

    product_id = serializers.UUIDField()
    product_name = serializers.CharField()
    brand = serializers.CharField()
    category = serializers.CharField()
    price = serializers.DecimalField(max_digits=12, decimal_places=2)
    thumbnail_url = serializers.URLField(required=False)
    score = serializers.FloatField()
    reason_codes = serializers.ListField(child=serializers.CharField())
    explanation = serializers.CharField(required=False, allow_blank=True)


class RecommendationsResponseSerializer(serializers.Serializer):
    """Serializer for recommendations response."""

    products = RecommendationSerializer(many=True)
    total_count = serializers.IntegerField()
    mode = serializers.CharField()
    generated_at = serializers.DateTimeField()


class KnowledgeDocumentSerializer(serializers.Serializer):
    """Serializer for knowledge documents."""

    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(max_length=255)
    document_type = serializers.ChoiceField(
        choices=[
            "faq",
            "return_policy",
            "payment_policy",
            "shipping_policy",
            "product_guide",
            "support_article",
        ]
    )
    source = serializers.CharField(max_length=100, default="internal")
    content = serializers.CharField()
    slug = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False, allow_null=True)
    is_active = serializers.BooleanField(default=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class ChatSessionSerializer(serializers.Serializer):
    """Serializer for chat sessions."""

    id = serializers.UUIDField(read_only=True)
    user_id = serializers.UUIDField(required=False, allow_null=True)
    session_title = serializers.CharField(required=False, allow_blank=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class ChatMessageSerializer(serializers.Serializer):
    """Serializer for chat messages."""

    id = serializers.UUIDField(read_only=True)
    session_id = serializers.UUIDField()
    role = serializers.ChoiceField(choices=["user", "assistant", "system"])
    content = serializers.CharField()
    metadata = serializers.JSONField(required=False, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)


class ChatAskSerializer(serializers.Serializer):
    """Serializer for chat ask endpoint."""

    session_id = serializers.UUIDField(required=False, allow_null=True)
    query = serializers.CharField()
    user_id = serializers.UUIDField(required=False, allow_null=True)
    context = serializers.JSONField(required=False, allow_null=True)


class ChatAnswerSerializer(serializers.Serializer):
    """Serializer for chat answer response."""

    session_id = serializers.UUIDField(required=False)
    answer = serializers.CharField()
    intent = serializers.CharField()
    sources = serializers.ListField()
    mode = serializers.CharField()
    related_products = serializers.ListField(required=False)
    confidence = serializers.FloatField(required=False)


class SourceSerializer(serializers.Serializer):
    """Serializer for knowledge sources."""

    document_id = serializers.CharField()
    chunk_index = serializers.IntegerField(required=False)
    document_title = serializers.CharField(required=False)
    document_type = serializers.CharField(required=False)
    source = serializers.CharField(required=False)
    snippet = serializers.CharField(required=False)


class GraphInsightSerializer(serializers.Serializer):
    """Serializer for graph insights."""

    user_id = serializers.CharField()
    top_brands = serializers.ListField()
    top_categories = serializers.ListField()
    top_price_ranges = serializers.ListField()


class BehaviorSummarySerializer(serializers.Serializer):
    """Serializer for aggregated behavior analytics."""

    total_events = serializers.IntegerField()
    unique_users = serializers.IntegerField()
    event_breakdown = serializers.ListField()
    top_viewed_categories = serializers.ListField()
    top_viewed_products = serializers.ListField()
    conversion_funnel = serializers.DictField()
    abandoned_cart_sessions = serializers.IntegerField()
    co_viewed_products = serializers.ListField()
    co_purchased_products = serializers.ListField()
    low_intent_users = serializers.IntegerField()
    user_segments = serializers.ListField()
    timeline = serializers.ListField()


class BehaviorUserSerializer(serializers.Serializer):
    """Serializer for per-user behavior analytics."""

    user_id = serializers.CharField()
    total_events = serializers.IntegerField()
    event_breakdown = serializers.ListField()
    dominant_categories = serializers.ListField()
    recent_searches = serializers.ListField()
    recent_timeline = serializers.ListField()
    current_intent = serializers.CharField()
    next_likely_actions = serializers.ListField()
    next_likely_products = serializers.ListField(required=False)


class BehaviorFunnelSerializer(serializers.Serializer):
    """Serializer for funnel analytics."""

    search_sessions = serializers.IntegerField()
    view_sessions = serializers.IntegerField()
    cart_sessions = serializers.IntegerField()
    checkout_sessions = serializers.IntegerField()
    order_sessions = serializers.IntegerField()
    payment_success_sessions = serializers.IntegerField()
