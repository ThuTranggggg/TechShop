"""
URL configuration for AI service API.
"""
from django.urls import path

from modules.ai.presentation.views import (
    AICartActionAPIView,
    AIOrderActionAPIView,
    BehaviorFunnelAPIView,
    BehaviorSummaryAPIView,
    BehaviorUserAPIView,
    CatalogSearchAPIView,
    ChatAskAPIView,
    ChatMessageAPIView,
    TrackEventAPIView,
    BulkTrackEventAPIView,
    UserPreferenceSummaryAPIView,
    RebuildProfileAPIView,
    RecommendationsAPIView,
    ChatSessionAPIView,
    KnowledgeDocumentAPIView,
    KnowledgeGraphRebuildAPIView,
    LSTMTrainAPIView,
    RagRebuildAPIView,
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
    path(
        "api/v1/ai/recommend/",
        RecommendationsAPIView.as_view(),
        name="recommendations_alias"
    ),
    path(
        "api/v1/ai/recommendations/<str:user_id>/",
        RecommendationsAPIView.as_view(),
        name="recommendations_by_user",
    ),
    path(
        "api/v1/ai/search/",
        CatalogSearchAPIView.as_view(),
        name="catalog_search",
    ),

    # Behavior analytics
    path(
        "api/v1/ai/behavior/summary/",
        BehaviorSummaryAPIView.as_view(),
        name="behavior_summary",
    ),
    path(
        "api/v1/ai/behavior/funnel/",
        BehaviorFunnelAPIView.as_view(),
        name="behavior_funnel",
    ),
    path(
        "api/v1/ai/behavior/users/<str:user_id>/",
        BehaviorUserAPIView.as_view(),
        name="behavior_user",
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
    path(
        "api/v1/ai/chat/",
        ChatAskAPIView.as_view(),
        name="chat_ask_alias",
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

    # AI actions
    path(
        "api/v1/ai/actions/add-to-cart/",
        AICartActionAPIView.as_view(),
        name="ai_add_to_cart",
    ),
    path(
        "api/v1/ai/actions/create-order/",
        AIOrderActionAPIView.as_view(),
        name="ai_create_order",
    ),

    # Admin AI operations
    path(
        "api/v1/ai/kg/rebuild/",
        KnowledgeGraphRebuildAPIView.as_view(),
        name="knowledge_graph_rebuild",
    ),
    path(
        "api/v1/ai/lstm/train/",
        LSTMTrainAPIView.as_view(),
        name="lstm_train",
    ),
    path(
        "api/v1/ai/rag/rebuild/",
        RagRebuildAPIView.as_view(),
        name="rag_rebuild",
    ),
]
