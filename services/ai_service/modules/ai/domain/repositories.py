"""
Domain repository interfaces.
Abstract interfaces for data persistence.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from uuid import UUID

from modules.ai.domain.entities import (
    BehavioralEvent,
    UserPreferenceProfile,
    KnowledgeDocument,
    KnowledgeChunk,
    ChatSession,
    ChatMessage,
)


class BehavioralEventRepository(ABC):
    """Repository interface for behavioral events."""

    @abstractmethod
    def add(self, event: BehavioralEvent) -> BehavioralEvent:
        """Add a new event."""
        pass

    @abstractmethod
    def add_bulk(self, events: List[BehavioralEvent]) -> List[BehavioralEvent]:
        """Add multiple events in bulk."""
        pass

    @abstractmethod
    def get_by_user(
        self,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[BehavioralEvent]:
        """Get events for a specific user."""
        pass

    @abstractmethod
    def get_recent_by_user(self, user_id: UUID, limit: int = 50) -> List[BehavioralEvent]:
        """Get recent events for a user."""
        pass

    @abstractmethod
    def get_by_product(self, product_id: UUID, limit: int = 100) -> List[BehavioralEvent]:
        """Get events related to a specific product."""
        pass


class UserPreferenceProfileRepository(ABC):
    """Repository interface for user preference profiles."""

    @abstractmethod
    def get_or_create(self, user_id: UUID) -> UserPreferenceProfile:
        """Get or create profile for a user."""
        pass

    @abstractmethod
    def save(self, profile: UserPreferenceProfile) -> UserPreferenceProfile:
        """Save/update a profile."""
        pass

    @abstractmethod
    def get_by_user_id(self, user_id: UUID) -> Optional[UserPreferenceProfile]:
        """Get profile for a user."""
        pass

    @abstractmethod
    def rebuild_profile_from_events(self, user_id: UUID) -> UserPreferenceProfile:
        """Rebuild profile from all user events."""
        pass


class KnowledgeDocumentRepository(ABC):
    """Repository interface for knowledge documents."""

    @abstractmethod
    def add(self, document: KnowledgeDocument) -> KnowledgeDocument:
        """Add a new document."""
        pass

    @abstractmethod
    def save(self, document: KnowledgeDocument) -> KnowledgeDocument:
        """Save/update a document."""
        pass

    @abstractmethod
    def get_by_id(self, document_id: UUID) -> Optional[KnowledgeDocument]:
        """Get document by ID."""
        pass

    @abstractmethod
    def get_active_documents(self, limit: int = 100) -> List[KnowledgeDocument]:
        """Get all active documents."""
        pass

    @abstractmethod
    def search_by_type(self, document_type: str) -> List[KnowledgeDocument]:
        """Search documents by type."""
        pass

    @abstractmethod
    def delete(self, document_id: UUID) -> None:
        """Delete a document."""
        pass


class KnowledgeChunkRepository(ABC):
    """Repository interface for knowledge chunks."""

    @abstractmethod
    def add(self, chunk: KnowledgeChunk) -> KnowledgeChunk:
        """Add a new chunk."""
        pass

    @abstractmethod
    def add_bulk(self, chunks: List[KnowledgeChunk]) -> List[KnowledgeChunk]:
        """Add multiple chunks."""
        pass

    @abstractmethod
    def get_by_document(self, document_id: UUID) -> List[KnowledgeChunk]:
        """Get all chunks for a document."""
        pass

    @abstractmethod
    def delete_by_document(self, document_id: UUID) -> int:
        """Delete all chunks for a document."""
        pass

    @abstractmethod
    def search_similar(self, query: str, limit: int = 5) -> List[KnowledgeChunk]:
        """Search similar chunks (keyword or semantic)."""
        pass


class ChatSessionRepository(ABC):
    """Repository interface for chat sessions."""

    @abstractmethod
    def create(self, session: ChatSession) -> ChatSession:
        """Create a new session."""
        pass

    @abstractmethod
    def get_by_id(self, session_id: UUID) -> Optional[ChatSession]:
        """Get session by ID."""
        pass

    @abstractmethod
    def get_by_user(self, user_id: UUID, limit: int = 20) -> List[ChatSession]:
        """Get sessions for a user."""
        pass

    @abstractmethod
    def save(self, session: ChatSession) -> ChatSession:
        """Save/update a session."""
        pass


class ChatMessageRepository(ABC):
    """Repository interface for chat messages."""

    @abstractmethod
    def add(self, message: ChatMessage) -> ChatMessage:
        """Add a message."""
        pass

    @abstractmethod
    def get_by_session(
        self,
        session_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ChatMessage]:
        """Get messages for a session."""
        pass

    @abstractmethod
    def get_n_latest_by_session(self, session_id: UUID, n: int = 10) -> List[ChatMessage]:
        """Get n latest messages from session."""
        pass
