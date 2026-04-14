"""
Django admin configuration for AI models.
"""
from django.contrib import admin
from modules.ai.infrastructure.models import (
    BehavioralEventModel,
    UserPreferenceProfileModel,
    KnowledgeDocumentModel,
    KnowledgeChunkModel,
    ChatSessionModel,
    ChatMessageModel,
    RecommendationCacheModel,
)


@admin.register(BehavioralEventModel)
class BehavioralEventAdmin(admin.ModelAdmin):
    """Admin for behavioral events."""

    list_display = (
        "event_type",
        "user_id",
        "product_id",
        "brand_name",
        "category_name",
        "occurred_at",
        "created_at",
    )
    list_filter = ("event_type", "brand_name", "category_name", "created_at")
    search_fields = ("user_id", "product_id", "brand_name", "category_name", "keyword")
    readonly_fields = ("id", "created_at")
    fieldsets = (
        ("Event Info", {"fields": ("id", "event_type", "occurred_at")}),
        ("User Context", {"fields": ("user_id", "session_id")}),
        ("Product Context", {"fields": ("product_id", "variant_id", "brand_name", "category_name")}),
        ("Price & Keyword", {"fields": ("price_amount", "price_range", "keyword")}),
        ("Source", {"fields": ("source_service", "metadata")}),
        ("Timestamp", {"fields": ("created_at",)}),
    )


@admin.register(UserPreferenceProfileModel)
class UserPreferenceProfileAdmin(admin.ModelAdmin):
    """Admin for user preference profiles."""

    list_display = (
        "user_id",
        "purchase_intent_score",
        "last_interaction_at",
        "updated_at",
    )
    list_filter = ("purchase_intent_score", "updated_at")
    search_fields = ("user_id",)
    readonly_fields = ("id", "created_at", "updated_at")
    fieldsets = (
        ("User", {"fields": ("id", "user_id")}),
        ("Preferences", {
            "fields": (
                "preferred_brands",
                "preferred_categories",
                "preferred_price_ranges",
                "recent_keywords",
            )
        }),
        ("Scores", {
            "fields": (
                "preference_score_summary",
                "purchase_intent_score",
            )
        }),
        ("Timestamps", {"fields": ("last_interaction_at", "created_at", "updated_at")}),
    )


@admin.register(KnowledgeDocumentModel)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    """Admin for knowledge documents."""

    list_display = (
        "title",
        "document_type",
        "source",
        "is_active",
        "created_at",
    )
    list_filter = ("document_type", "is_active", "created_at")
    search_fields = ("title", "content")
    readonly_fields = ("id", "created_at", "updated_at")
    fieldsets = (
        ("Document Info", {
            "fields": ("id", "title", "slug", "document_type", "source")
        }),
        ("Content", {"fields": ("content",)}),
        ("Settings", {"fields": ("is_active", "metadata")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(KnowledgeChunkModel)
class KnowledgeChunkAdmin(admin.ModelAdmin):
    """Admin for knowledge chunks."""

    list_display = (
        "id",
        "document",
        "chunk_index",
        "created_at",
    )
    list_filter = ("document", "created_at")
    search_fields = ("content", "document__title")
    readonly_fields = ("id", "created_at")
    fieldsets = (
        ("Chunk Info", {"fields": ("id", "document", "chunk_index")}),
        ("Content", {"fields": ("content",)}),
        ("Embedding", {"fields": ("embedding_ref",)}),
        ("Metadata", {"fields": ("metadata",)}),
        ("Timestamp", {"fields": ("created_at",)}),
    )


@admin.register(ChatSessionModel)
class ChatSessionAdmin(admin.ModelAdmin):
    """Admin for chat sessions."""

    list_display = (
        "id",
        "user_id",
        "session_title",
        "created_at",
        "updated_at",
    )
    list_filter = ("created_at", "updated_at")
    search_fields = ("user_id", "session_title")
    readonly_fields = ("id", "created_at", "updated_at")
    fieldsets = (
        ("Session Info", {"fields": ("id", "user_id", "session_title")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(ChatMessageModel)
class ChatMessageAdmin(admin.ModelAdmin):
    """Admin for chat messages."""

    list_display = (
        "id",
        "session",
        "role",
        "created_at",
    )
    list_filter = ("role", "created_at")
    search_fields = ("content", "session__session_title")
    readonly_fields = ("id", "created_at")
    fieldsets = (
        ("Message Info", {"fields": ("id", "session", "role")}),
        ("Content", {"fields": ("content",)}),
        ("Metadata", {"fields": ("metadata",)}),
        ("Timestamp", {"fields": ("created_at",)}),
    )


@admin.register(RecommendationCacheModel)
class RecommendationCacheAdmin(admin.ModelAdmin):
    """Admin for recommendation cache."""

    list_display = (
        "user_id",
        "recommendation_type",
        "generated_at",
        "expires_at",
    )
    list_filter = ("recommendation_type", "generated_at", "expires_at")
    search_fields = ("user_id",)
    readonly_fields = ("id", "generated_at")
    fieldsets = (
        ("Cache Info", {"fields": ("id", "user_id", "recommendation_type")}),
        ("Result", {"fields": ("result_payload",)}),
        ("Timestamps", {"fields": ("generated_at", "expires_at")}),
    )
