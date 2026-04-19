"""
Infrastructure layer - Django ORM models.
Database persistence layer.
"""
from django.db import models
from uuid import uuid4
from pgvector.django import VectorField

from modules.ai.domain.value_objects import (
    EventType,
    PriceRange,
    DocumentType,
    ChatRole,
)


class BehavioralEventModel(models.Model):
    """Django model for behavioral events."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    event_type = models.CharField(
        max_length=30,
        choices=[(e.value, e.value) for e in EventType],
        db_index=True,
    )
    user_id = models.UUIDField(null=True, blank=True, db_index=True)
    session_id = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    product_id = models.UUIDField(null=True, blank=True, db_index=True)
    variant_id = models.UUIDField(null=True, blank=True)
    brand_name = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    category_name = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    price_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_range = models.CharField(
        max_length=20,
        choices=[(p.value, p.value) for p in PriceRange],
        null=True,
        blank=True,
        db_index=True,
    )
    keyword = models.CharField(max_length=255, null=True, blank=True)
    source_service = models.CharField(max_length=50, null=True, blank=True)
    occurred_at = models.DateTimeField(db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "behavioral_event"
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["user_id", "created_at"]),
            models.Index(fields=["product_id"]),
            models.Index(fields=["brand_name", "category_name"]),
            models.Index(fields=["price_range"]),
        ]
        verbose_name = "Behavioral Event"
        verbose_name_plural = "Behavioral Events"
        ordering = ["-occurred_at"]

    def __str__(self):
        return f"{self.event_type} - {self.user_id or 'anonymous'}"


class UserPreferenceProfileModel(models.Model):
    """Django model for user preference profiles."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user_id = models.UUIDField(unique=True, db_index=True)
    
    # Preferences stored as JSON
    preferred_brands = models.JSONField(
        default=list,
        blank=True,
        help_text="List of brand preferences with scores"
    )
    preferred_categories = models.JSONField(
        default=list,
        blank=True,
        help_text="List of category preferences with scores"
    )
    preferred_price_ranges = models.JSONField(
        default=list,
        blank=True,
        help_text="List of price range preferences with scores"
    )
    recent_keywords = models.JSONField(
        default=list,
        blank=True,
        help_text="Recent search keywords"
    )
    
    # Score fields
    preference_score_summary = models.JSONField(
        default=dict,
        blank=True,
        help_text="Summary of various preference scores"
    )
    purchase_intent_score = models.FloatField(
        default=0.0,
        db_index=True,
        help_text="Score indicating purchase likelihood (0-100)"
    )
    
    last_interaction_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        db_table = "user_preference_profile"
        indexes = [
            models.Index(fields=["purchase_intent_score"]),
            models.Index(fields=["updated_at"]),
        ]
        verbose_name = "User Preference Profile"
        verbose_name_plural = "User Preference Profiles"

    def __str__(self):
        return f"Profile for user {self.user_id}"


class KnowledgeDocumentModel(models.Model):
    """Django model for knowledge documents."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    document_type = models.CharField(
        max_length=30,
        choices=[(d.value, d.value) for d in DocumentType],
        db_index=True,
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True)
    source = models.CharField(max_length=100, default="internal")
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "knowledge_document"
        indexes = [
            models.Index(fields=["document_type", "is_active"]),
        ]
        verbose_name = "Knowledge Document"
        verbose_name_plural = "Knowledge Documents"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.document_type})"


class KnowledgeChunkModel(models.Model):
    """Django model for knowledge chunks (RAG)."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    document = models.ForeignKey(
        KnowledgeDocumentModel,
        on_delete=models.CASCADE,
        related_name="chunks"
    )
    chunk_index = models.IntegerField()
    content = models.TextField()
    embedding_ref = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Reference to external embedding or vector store"
    )
    embedding = VectorField(dimensions=1536, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "knowledge_chunk"
        indexes = [
            models.Index(fields=["document_id", "chunk_index"]),
        ]
        unique_together = ("document", "chunk_index")
        verbose_name = "Knowledge Chunk"
        verbose_name_plural = "Knowledge Chunks"

    def __str__(self):
        return f"Chunk {self.chunk_index} of {self.document.title}"


class ChatSessionModel(models.Model):
    """Django model for chat sessions."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user_id = models.UUIDField(null=True, blank=True, db_index=True)
    session_title = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        db_table = "chat_session"
        indexes = [
            models.Index(fields=["user_id", "updated_at"]),
        ]
        verbose_name = "Chat Session"
        verbose_name_plural = "Chat Sessions"
        ordering = ["-updated_at"]

    def __str__(self):
        title = self.session_title or f"Session {self.id}"
        user = f" ({self.user_id})" if self.user_id else ""
        return f"{title}{user}"


class ChatMessageModel(models.Model):
    """Django model for chat messages."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    session = models.ForeignKey(
        ChatSessionModel,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    role = models.CharField(
        max_length=20,
        choices=[(r.value, r.value) for r in ChatRole],
        db_index=True,
    )
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "chat_message"
        indexes = [
            models.Index(fields=["session_id", "role", "created_at"]),
        ]
        verbose_name = "Chat Message"
        verbose_name_plural = "Chat Messages"
        ordering = ["created_at"]

    def __str__(self):
        content_preview = self.content[:50]
        return f"{self.role}: {content_preview}..."


class RecommendationCacheModel(models.Model):
    """Optional cache for recommendations."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user_id = models.UUIDField(null=True, blank=True, db_index=True)
    recommendation_type = models.CharField(
        max_length=50,
        db_index=True,
        help_text="personalized, fallback, related, trending"
    )
    result_payload = models.JSONField()
    generated_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "recommendation_cache"
        indexes = [
            models.Index(fields=["user_id", "recommendation_type"]),
            models.Index(fields=["expires_at"]),
        ]
        verbose_name = "Recommendation Cache"
        verbose_name_plural = "Recommendation Caches"
        ordering = ["-generated_at"]

    def __str__(self):
        return f"{self.recommendation_type} for {self.user_id or 'anonymous'}"
