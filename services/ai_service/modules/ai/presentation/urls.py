"""
URL configuration for AI service API.
"""
from django.urls import path

from modules.ai.presentation.views import (
    TrackEventAPIView,
    BulkTrackEventAPIView,
    UserPreferenceSummaryAPIView,
    RebuildProfileAPIView,
    RecommendationsAPIView,
    ChatSessionAPIView,
    ChatAskAPIView,
    ChatMessageAPIView,
    KnowledgeDocumentAPIView,
)

app_name = "ai_api"

urlpatterns = [
    # Event tracking
    path(
        "api/v1/ai/events/track/",
        TrackEventAPIView.as_view(),
        name="track_event"
    ),
    path(
        "api/v1/ai/events/bulk/",
        BulkTrackEventAPIView.as_view(),
        name="bulk_track_events"
    ),
    path(
        "api/v1/internal/ai/events/",
        BulkTrackEventAPIView.as_view(),
        name="internal_track_events"
    ),

    # User preferences
    path(
        "api/v1/ai/users/<str:user_id>/preferences/",
        UserPreferenceSummaryAPIView.as_view(),
        name="user_preferences"
    ),
    path(
        "api/v1/admin/ai/users/<str:user_id>/rebuild-profile/",
        RebuildProfileAPIView.as_view(),
        name="rebuild_profile"
    ),

    # Recommendations
    path(
        "api/v1/ai/recommendations/",
        RecommendationsAPIView.as_view(),
        name="recommendations"
    ),

    # Chat sessions
    path(
        "api/v1/ai/chat/sessions/",
        ChatSessionAPIView.as_view(),
        name="chat_sessions"
    ),
    path(
        "api/v1/ai/chat/sessions/<str:session_id>/",
        ChatSessionAPIView.as_view(),
        name="chat_session_detail"
    ),

    # Chat messages
    path(
        "api/v1/ai/chat/messages/",
        ChatMessageAPIView.as_view(),
        name="chat_messages"
    ),

    # Chat ask
    path(
        "api/v1/ai/chat/ask/",
        ChatAskAPIView.as_view(),
        name="chat_ask"
    ),

    # Knowledge documents
    path(
        "api/v1/admin/ai/knowledge/",
        KnowledgeDocumentAPIView.as_view(),
        name="knowledge_documents"
    ),
    path(
        "api/v1/admin/ai/knowledge/<str:doc_id>/",
        KnowledgeDocumentAPIView.as_view(),
        name="knowledge_document_detail"
    ),
]
