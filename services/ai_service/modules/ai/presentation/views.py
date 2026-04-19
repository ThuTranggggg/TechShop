"""
Presentation layer - API Views.
"""
import logging
from io import StringIO
from uuid import UUID

from django.core.management import call_command
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from common.responses import success_response, error_response

from modules.ai.application.services import (
    AiCartActionUseCase,
    AiOrderActionUseCase,
    BehaviorAnalyticsUseCase,
    CatalogSearchUseCase,
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
from modules.ai.presentation.serializers import (
    BehaviorFunnelSerializer,
    BehaviorSummarySerializer,
    BehaviorUserSerializer,
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
from modules.ai.infrastructure.providers import get_llm_provider
from modules.ai.infrastructure.repositories import (
    DjangoKnowledgeDocumentRepository,
    DjangoChatSessionRepository,
    DjangoChatMessageRepository,
)
from modules.ai.infrastructure.models import KnowledgeDocumentModel

logger = logging.getLogger(__name__)


def _is_admin_or_staff_request(request) -> bool:
    role = request.headers.get("X-User-Role", "").lower()
    if role in {"admin", "staff"}:
        return True
    return request.headers.get("X-Admin", "").lower() == "true"


def _safe_uuid(raw_value):
    try:
        return UUID(str(raw_value))
    except (TypeError, ValueError):
        return None


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
                occurred_at=data.get("occurred_at"),
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

    def get(self, request, user_id=None):
        """Get recommendation list from live catalog using user/query context."""
        raw_user_id = user_id or request.query_params.get("user_id")
        query = request.query_params.get("query", "")
        limit = int(request.query_params.get("limit", 10))

        user_id = None
        if raw_user_id:
            try:
                user_id = UUID(raw_user_id)
            except (ValueError, TypeError):
                return error_response("Invalid user ID", "user_id must be UUID", status.HTTP_400_BAD_REQUEST)

        use_case = GenerateRecommendationsUseCase()
        try:
            provider = get_llm_provider()
            entities = provider.maybe_extract_entities(query) if query else {}
            result = use_case.recommend_from_catalog(user_id=user_id, query=query, limit=limit, entities=entities)
            return success_response("Recommendations", result)
        except Exception as e:
            logger.error(f"Error generating catalog recommendations: {e}")
            return error_response("Error", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """Get recommendations for products."""
        products = request.data.get("products", [])
        user_id = request.data.get("user_id")
        limit = request.data.get("limit", 10)
        query = request.data.get("query", "")

        if not products:
            return error_response("Invalid request", "products required", status.HTTP_400_BAD_REQUEST)

        if user_id:
            try:
                user_id = UUID(user_id)
            except (ValueError, TypeError):
                pass

        use_case = GenerateRecommendationsUseCase()
        try:
            scored_products = use_case.score_products(products, user_id=user_id, query=query)
            top_products = scored_products[:limit]

            result = {
                "products": top_products,
                "total_count": len(top_products),
                "mode": "hybrid_personalized" if user_id else "hybrid_anonymous",
                "generated_at": timezone.now().isoformat(),
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
            session_id = data.get("session_id")
            chat_history = None

            if session_id:
                session = DjangoChatSessionRepository().get_by_id(session_id)
                if not session:
                    return error_response("Not found", "Session not found", status.HTTP_404_NOT_FOUND)

                recent_messages = DjangoChatMessageRepository().get_n_latest_by_session(session_id, n=10)
                chat_history = [
                    {"role": message.role.value, "content": message.content}
                    for message in recent_messages
                ]

            answer_data = use_case.execute(
                query=query,
                user_id=user_id,
                user_context=context,
                chat_history=chat_history,
            )

            if user_id:
                try:
                    TrackBehavioralEventUseCase().execute(
                        event_type="chat_query",
                        user_id=user_id,
                        keyword=query,
                        source_service="chatbot",
                        metadata={"intent": answer_data.get("intent"), "session_id": str(session_id) if session_id else None},
                    )
                except Exception as event_exc:
                    logger.warning(f"Could not track chat_query event: {event_exc}")

            if session_id:
                append_message = AppendChatMessageUseCase()
                append_message.execute(session_id=session_id, role="user", content=query)
                append_message.execute(
                    session_id=session_id,
                    role="assistant",
                    content=answer_data["answer"],
                    metadata={"sources": answer_data.get("sources", [])},
                )
                answer_data["session_id"] = str(session_id)

            return success_response("Answer", answer_data)
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return error_response("Error", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


class CatalogSearchAPIView(APIView):
    """AI-assisted catalog search endpoint."""

    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        limit = int(request.query_params.get("limit", 10))
        raw_user_id = request.query_params.get("user_id")
        user_id = None

        if raw_user_id:
            try:
                user_id = UUID(raw_user_id)
            except (TypeError, ValueError):
                return error_response("Invalid user ID", "user_id must be UUID", status.HTTP_400_BAD_REQUEST)

        try:
            result = CatalogSearchUseCase().execute(query=query, user_id=user_id, limit=limit)
            return success_response("Catalog search", result)
        except Exception as exc:
            logger.error(f"Error performing AI catalog search: {exc}")
            return error_response("Error", str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)


class BehaviorSummaryAPIView(APIView):
    """Get aggregate behavior analytics."""

    permission_classes = [AllowAny]

    def get(self, request):
        try:
            summary = BehaviorAnalyticsUseCase().get_summary()
            serializer = BehaviorSummarySerializer(summary)
            return success_response("Behavior summary", serializer.data)
        except Exception as exc:
            logger.error(f"Error building behavior summary: {exc}")
            return error_response("Error", str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)


class BehaviorUserAPIView(APIView):
    """Get analytics for one user."""

    permission_classes = [AllowAny]

    def get(self, request, user_id):
        try:
            summary = BehaviorAnalyticsUseCase().get_user_summary(UUID(user_id))
            serializer = BehaviorUserSerializer(summary)
            return success_response("Behavior user summary", serializer.data)
        except ValueError:
            return error_response("Invalid user ID", "user_id must be UUID", status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.error(f"Error building user behavior summary: {exc}")
            return error_response("Error", str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)


class BehaviorFunnelAPIView(APIView):
    """Get conversion funnel analytics."""

    permission_classes = [AllowAny]

    def get(self, request):
        try:
            summary = BehaviorAnalyticsUseCase().get_funnel()
            serializer = BehaviorFunnelSerializer(summary)
            return success_response("Behavior funnel", serializer.data)
        except Exception as exc:
            logger.error(f"Error building behavior funnel: {exc}")
            return error_response("Error", str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)


class AICartActionAPIView(APIView):
    """Add items to cart via AI service."""

    permission_classes = [AllowAny]

    def post(self, request):
        raw_user_id = request.data.get("user_id")
        if not raw_user_id:
            return error_response("Invalid request", "user_id is required", status.HTTP_400_BAD_REQUEST)

        try:
            user_id = UUID(str(raw_user_id))
        except ValueError:
            return error_response("Invalid user ID", "user_id must be UUID", status.HTTP_400_BAD_REQUEST)

        product_id = request.data.get("product_id")
        quantity = int(request.data.get("quantity", 1))
        if not product_id:
            return error_response("Invalid request", "product_id is required", status.HTTP_400_BAD_REQUEST)

        try:
            result = AiCartActionUseCase().execute(
                user_id=user_id,
                product_id=str(product_id),
                quantity=quantity,
                variant_id=request.data.get("variant_id"),
            )
            TrackBehavioralEventUseCase().execute(
                event_type="add_to_cart",
                user_id=user_id,
                product_id=_safe_uuid(product_id),
                source_service="ai_action",
                metadata={"source": "ai_service_action"},
            )
            return success_response("Added to cart", result, status.HTTP_201_CREATED)
        except Exception as exc:
            logger.error(f"Error adding item to cart through AI service: {exc}")
            return error_response("Error", str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)


class AIOrderActionAPIView(APIView):
    """Create orders via AI service."""

    permission_classes = [AllowAny]

    def post(self, request):
        raw_user_id = request.data.get("user_id")
        cart_id = request.data.get("cart_id")
        shipping_address = request.data.get("shipping_address") or {}

        if not raw_user_id or not cart_id:
            return error_response("Invalid request", "user_id and cart_id are required", status.HTTP_400_BAD_REQUEST)

        try:
            user_id = UUID(str(raw_user_id))
        except ValueError:
            return error_response("Invalid user ID", "user_id must be UUID", status.HTTP_400_BAD_REQUEST)

        try:
            result = AiOrderActionUseCase().execute(
                user_id=user_id,
                cart_id=str(cart_id),
                shipping_address=shipping_address,
                notes=str(request.data.get("notes") or ""),
            )
            return success_response("Order created", result, status.HTTP_201_CREATED)
        except Exception as exc:
            logger.error(f"Error creating order through AI service: {exc}")
            return error_response("Error", str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)


class KnowledgeGraphRebuildAPIView(APIView):
    """Trigger Neo4j knowledge-graph rebuild."""

    permission_classes = [AllowAny]

    def post(self, request):
        if not _is_admin_or_staff_request(request):
            return error_response("Forbidden", "Admin or staff role required", status.HTTP_403_FORBIDDEN)

        output = StringIO()
        try:
            call_command(
                "rebuild_knowledge_graph",
                clear=bool(request.data.get("clear_graph", True)),
                stdout=output,
            )
            return success_response("Knowledge graph rebuilt", {"output": output.getvalue()})
        except Exception as exc:
            logger.error(f"Error rebuilding knowledge graph: {exc}")
            return error_response("Error", str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)


class LSTMTrainAPIView(APIView):
    """Trigger LSTM training."""

    permission_classes = [AllowAny]

    def post(self, request):
        if not _is_admin_or_staff_request(request):
            return error_response("Forbidden", "Admin or staff role required", status.HTTP_403_FORBIDDEN)

        output = StringIO()
        try:
            call_command(
                "train_lstm_recommender",
                dataset=request.data.get("dataset") or None,
                epochs=int(request.data.get("epochs", 8)),
                sequence_length=int(request.data.get("sequence_length", 5)),
                batch_size=int(request.data.get("batch_size", 16)),
                stdout=output,
            )
            return success_response("LSTM training completed", {"output": output.getvalue()})
        except Exception as exc:
            logger.error(f"Error training LSTM model: {exc}")
            return error_response("Error", str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)


class RagRebuildAPIView(APIView):
    """Trigger local RAG index rebuild."""

    permission_classes = [AllowAny]

    def post(self, request):
        if not _is_admin_or_staff_request(request):
            return error_response("Forbidden", "Admin or staff role required", status.HTTP_403_FORBIDDEN)

        output = StringIO()
        try:
            call_command(
                "build_rag_index",
                replace=bool(request.data.get("replace", True)),
                stdout=output,
            )
            return success_response("RAG index rebuilt", {"output": output.getvalue()})
        except Exception as exc:
            logger.error(f"Error rebuilding RAG index: {exc}")
            return error_response("Error", str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)


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
                        "source": doc.source,
                        "content_preview": doc.content[:180],
                        "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    }
                    for doc in docs
                ]
                return success_response("Documents", {"documents": data, "count": len(data)})
            except Exception as e:
                logger.error(f"Error listing documents: {e}")
                return error_response("Error", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)
