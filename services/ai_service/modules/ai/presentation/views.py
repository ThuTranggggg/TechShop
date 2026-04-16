"""
Presentation layer - API Views.
"""
import logging
from datetime import datetime
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from uuid import UUID
import uuid

from common.responses import success_response, error_response

from modules.ai.application.services import (
    TrackBehavioralEventUseCase,
    BulkTrackBehavioralEventsUseCase,
    RebuildUserPreferenceProfileUseCase,
    GetUserPreferenceSummaryUseCase,
    GenerateRecommendationsUseCase,
    IngestKnowledgeDocumentUseCase,
    CreateChatSessionUseCase,
    AppendChatMessageUseCase,
    GenerateChatAnswerUseCase,
)
from modules.ai.infrastructure.providers import (
    AIConfigurationError,
    AIUpstreamError,
    AIUpstreamTimeout,
)
from modules.ai.presentation.serializers import (
    BehavioralEventSerializer,
    BulkBehavioralEventSerializer,
    UserPreferenceSummarySerializer,
    RecommendationsResponseSerializer,
    RecommendationSerializer,
    KnowledgeDocumentSerializer,
    ChatSessionSerializer,
    ChatMessageSerializer,
    ChatAskSerializer,
    ChatAnswerSerializer,
)
from modules.ai.infrastructure.repositories import (
    DjangoKnowledgeDocumentRepository,
    DjangoChatSessionRepository,
    DjangoChatMessageRepository,
)
from modules.ai.infrastructure.models import (
    BehavioralEventModel,
    KnowledgeDocumentModel,
    ChatSessionModel,
    ChatMessageModel,
)

logger = logging.getLogger(__name__)


class TrackEventAPIView(APIView):
    """Track a single behavioral event."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Track event."""
        serializer = BehavioralEventSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Validation error", serializer.errors, status.HTTP_400_BAD_REQUEST)

        use_case = TrackBehavioralEventUseCase()
        try:
            data = serializer.validated_data
            event = use_case.execute(
                event_type=data["event_type"],
                user_id=data.get("user_id"),
                session_id=data.get("session_id"),
                product_id=data.get("product_id"),
                variant_id=data.get("variant_id"),
                brand_name=data.get("brand_name"),
                category_name=data.get("category_name"),
                price_amount=float(data["price_amount"]) if data.get("price_amount") else None,
                keyword=data.get("keyword"),
                source_service=data.get("source_service"),
                metadata=data.get("metadata", {}),
            )
            return success_response(
                "Event tracked",
                {"event_id": str(event.id)},
                status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error(f"Error tracking event: {e}")
            return error_response("Error tracking event", str(e), status.HTTP_400_BAD_REQUEST)


class BulkTrackEventAPIView(APIView):
    """Track multiple events in bulk."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Bulk track events."""
        serializer = BulkBehavioralEventSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Validation error", serializer.errors, status.HTTP_400_BAD_REQUEST)

        use_case = BulkTrackBehavioralEventsUseCase()
        try:
            events_data = serializer.validated_data["events"]
            events = use_case.execute(events_data)
            return success_response(
                f"Tracked {len(events)} events",
                {"count": len(events)},
                status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error(f"Error bulk tracking: {e}")
            return error_response("Error bulk tracking", str(e), status.HTTP_400_BAD_REQUEST)


class UserPreferenceSummaryAPIView(APIView):
    """Get user preference summary."""

    permission_classes = [AllowAny]

    def get(self, request, user_id):
        """Get preference summary."""
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            return error_response("Invalid user ID", "user_id must be UUID", status.HTTP_400_BAD_REQUEST)

        use_case = GetUserPreferenceSummaryUseCase()
        try:
            summary = use_case.execute(user_uuid)
            if not summary:
                return error_response("Not found", "User profile not found", status.HTTP_404_NOT_FOUND)

            serializer = UserPreferenceSummarySerializer(summary)
            return success_response("User preferences", serializer.data)
        except Exception as e:
            logger.error(f"Error getting preferences: {e}")
            return error_response("Error", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


class RebuildProfileAPIView(APIView):
    """Rebuild user profile from events (admin)."""

    permission_classes = [AllowAny]  # Should add proper auth

    def post(self, request, user_id):
        """Rebuild profile."""
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            return error_response("Invalid user ID", "user_id must be UUID", status.HTTP_400_BAD_REQUEST)

        use_case = RebuildUserPreferenceProfileUseCase()
        try:
            profile = use_case.execute(user_uuid)
            return success_response(
                "Profile rebuilt",
                {"user_id": str(user_uuid), "updated_at": profile.updated_at.isoformat() if profile.updated_at else None}
            )
        except Exception as e:
            logger.error(f"Error rebuilding profile: {e}")
            return error_response("Error", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


class RecommendationsAPIView(APIView):
    """Get recommendations."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Get recommendations for products."""
        products = request.data.get("products", [])
        user_id = request.data.get("user_id")
        limit = request.data.get("limit", 10)

        if not products:
            return error_response("Invalid request", "products required", status.HTTP_400_BAD_REQUEST)

        if user_id:
            try:
                user_id = UUID(user_id)
            except (ValueError, TypeError):
                pass

        use_case = GenerateRecommendationsUseCase()
        try:
            scored_products = use_case.score_products(products, user_id=user_id)
            top_products = scored_products[:limit]

            result = {
                "products": top_products,
                "total_count": len(top_products),
                "mode": "personalized" if user_id else "anonymous",
                "generated_at": datetime.utcnow().isoformat() + "Z",
            }
            return success_response("Recommendations", result)
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return error_response("Error", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChatSessionAPIView(APIView):
    """Manage chat sessions."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Create chat session."""
        use_case = CreateChatSessionUseCase()
        try:
            user_id = request.data.get("user_id")
            if user_id:
                try:
                    user_id = UUID(user_id)
                except (ValueError, TypeError):
                    pass

            session_title = request.data.get("session_title")

            session = use_case.execute(user_id=user_id, session_title=session_title)

            serializer = ChatSessionSerializer({"id": session.id, "user_id": session.user_id, "session_title": session.session_title, "created_at": session.created_at, "updated_at": session.updated_at})
            return success_response(
                "Session created",
                serializer.data,
                status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return error_response("Error", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request, session_id=None):
        """Get chat session."""
        if not session_id:
            return error_response("Invalid request", "session_id required", status.HTTP_400_BAD_REQUEST)

        try:
            session_uuid = UUID(session_id)
        except ValueError:
            return error_response("Invalid session ID", "session_id must be UUID", status.HTTP_400_BAD_REQUEST)

        repo = DjangoChatSessionRepository()
        try:
            session = repo.get_by_id(session_uuid)
            if not session:
                return error_response("Not found", "Session not found", status.HTTP_404_NOT_FOUND)

            # Get messages
            msg_repo = DjangoChatMessageRepository()
            messages = msg_repo.get_by_session(session_uuid)

            serializer = ChatSessionSerializer({
                "id": session.id,
                "user_id": session.user_id,
                "session_title": session.session_title,
                "created_at": session.created_at,
                "updated_at": session.updated_at,
            })

            return success_response("Session", {
                **serializer.data,
                "messages": [
                    {
                        "id": str(m.id),
                        "role": m.role.value,
                        "content": m.content,
                        "created_at": m.created_at.isoformat() if m.created_at else None,
                    }
                    for m in messages
                ]
            })
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            return error_response("Error", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChatAskAPIView(APIView):
    """Chat ask endpoint."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Ask a question."""
        serializer = ChatAskSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Validation error", serializer.errors, status.HTTP_400_BAD_REQUEST)

        use_case = GenerateChatAnswerUseCase()
        try:
            data = serializer.validated_data
            query = data["query"]
            user_id = data.get("user_id")
            context = data.get("context")

            answer_data = use_case.execute(
                query=query,
                user_id=user_id,
                session_id=data.get("session_id"),
                user_context=context,
            )

            return success_response("Answer", answer_data)
        except AIConfigurationError as e:
            logger.error(f"AI config error: {e}")
            return error_response("AI configuration error", str(e), status.HTTP_503_SERVICE_UNAVAILABLE)
        except AIUpstreamTimeout as e:
            logger.error(f"AI timeout: {e}")
            return error_response("AI provider timeout", str(e), status.HTTP_504_GATEWAY_TIMEOUT)
        except AIUpstreamError as e:
            logger.error(f"AI upstream error: {e}")
            return error_response("AI provider error", str(e), status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return error_response("Error", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChatMessageAPIView(APIView):
    """Add message to chat."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Add message."""
        serializer = ChatMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Validation error", serializer.errors, status.HTTP_400_BAD_REQUEST)

        use_case = AppendChatMessageUseCase()
        try:
            data = serializer.validated_data
            message = use_case.execute(
                session_id=data["session_id"],
                role=data["role"],
                content=data["content"],
                metadata=data.get("metadata"),
            )

            return success_response(
                "Message added",
                {"message_id": str(message.id)},
                status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            return error_response("Error", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


class KnowledgeDocumentAPIView(APIView):
    """Manage knowledge documents."""

    permission_classes = [AllowAny]  # Should use admin permission

    def post(self, request):
        """Create knowledge document."""
        serializer = KnowledgeDocumentSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Validation error", serializer.errors, status.HTTP_400_BAD_REQUEST)

        use_case = IngestKnowledgeDocumentUseCase()
        try:
            data = serializer.validated_data
            result = use_case.execute(
                title=data["title"],
                content=data["content"],
                document_type=data["document_type"],
                source=data.get("source", "internal"),
                slug=data.get("slug"),
                metadata=data.get("metadata"),
            )

            return success_response(
                "Document created",
                result,
                status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error(f"Error creating document: {e}")
            return error_response("Error", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request, doc_id=None):
        """Get knowledge documents."""
        if doc_id:
            try:
                doc_uuid = UUID(doc_id)
            except ValueError:
                return error_response("Invalid doc ID", "doc_id must be UUID", status.HTTP_400_BAD_REQUEST)

            repo = DjangoKnowledgeDocumentRepository()
            try:
                doc = repo.get_by_id(doc_uuid)
                if not doc:
                    return error_response("Not found", "Document not found", status.HTTP_404_NOT_FOUND)

                data = {
                    "id": str(doc.id),
                    "title": doc.title,
                    "document_type": doc.document_type.value,
                    "source": doc.source,
                    "content": doc.content,
                    "is_active": doc.is_active,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                }
                return success_response("Document", data)
            except Exception as e:
                logger.error(f"Error getting document: {e}")
                return error_response("Error", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            # List documents
            try:
                docs = KnowledgeDocumentModel.objects.filter(is_active=True)[:100]
                data = [
                    {
                        "id": str(doc.id),
                        "title": doc.title,
                        "document_type": doc.document_type,
                        "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    }
                    for doc in docs
                ]
                return success_response("Documents", {"documents": data, "count": len(data)})
            except Exception as e:
                logger.error(f"Error listing documents: {e}")
                return error_response("Error", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)
