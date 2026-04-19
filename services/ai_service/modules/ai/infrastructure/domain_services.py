"""
Infrastructure domain services implementations.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from django.conf import settings
from neo4j import GraphDatabase

from modules.ai.domain.entities import BehavioralEvent, KnowledgeChunk, UserPreferenceProfile
from modules.ai.domain.services import (
    GraphService,
    PreferenceProfileBuilder,
    PriceRangeNormalizer,
    RecommendationScorer,
    RetrievalService,
)
from modules.ai.domain.value_objects import (
    BrandPreference,
    CategoryPreference,
    EventType,
    PriceRange,
    PriceRangePreference,
)
from modules.ai.infrastructure.repositories import DjangoKnowledgeChunkRepository
from modules.ai.infrastructure.sequence_models import SequenceRecommendationService
from modules.ai.infrastructure.taxonomy import normalize_text, tokenize

logger = logging.getLogger(__name__)


class DefaultPriceRangeNormalizer(PriceRangeNormalizer):
    """Default price range normalization for Vietnamese market."""

    RANGES = [
        (0, 1_000_000, PriceRange.UNDER_1M),
        (1_000_000, 3_000_000, PriceRange.FROM_1M_TO_3M),
        (3_000_000, 5_000_000, PriceRange.FROM_3M_TO_5M),
        (5_000_000, 10_000_000, PriceRange.FROM_5M_TO_10M),
        (10_000_000, 20_000_000, PriceRange.FROM_10M_TO_20M),
        (20_000_000, float("inf"), PriceRange.ABOVE_20M),
    ]

    def normalize_price(self, amount: float) -> PriceRange:
        for min_val, max_val, range_enum in self.RANGES:
            if min_val <= amount < max_val:
                return range_enum
        return PriceRange.ABOVE_20M

    def get_all_ranges(self) -> List[PriceRange]:
        return [
            PriceRange.UNDER_1M,
            PriceRange.FROM_1M_TO_3M,
            PriceRange.FROM_3M_TO_5M,
            PriceRange.FROM_5M_TO_10M,
            PriceRange.FROM_10M_TO_20M,
            PriceRange.ABOVE_20M,
        ]


class EventBasedPreferenceProfileBuilder(PreferenceProfileBuilder):
    """Build user preference profiles from behavioral events."""

    def __init__(self, price_normalizer: Optional[PriceRangeNormalizer] = None):
        self.price_normalizer = price_normalizer or DefaultPriceRangeNormalizer()

    def build_profile_from_events(self, user_id: UUID, events: List[BehavioralEvent]) -> UserPreferenceProfile:
        profile = UserPreferenceProfile(id=user_id, user_id=user_id)
        for event in events:
            profile = self.update_profile_with_event(profile, event)
        return profile

    def update_profile_with_event(self, profile: UserPreferenceProfile, event: BehavioralEvent) -> UserPreferenceProfile:
        if not event.has_product_context():
            return profile

        score_delta = event.get_behavior_score()

        if event.brand_name:
            profile.preferred_brands = self._update_brand_preferences(
                profile.preferred_brands,
                event.brand_name,
                score_delta,
            )

        if event.category_name:
            profile.preferred_categories = self._update_category_preferences(
                profile.preferred_categories,
                event.category_name,
                score_delta,
            )

        if event.price_amount is not None:
            price_range = self.price_normalizer.normalize_price(float(event.price_amount))
            profile.preferred_price_ranges = self._update_price_preferences(
                profile.preferred_price_ranges,
                price_range,
                score_delta,
            )

        if event.keyword:
            keywords = list(profile.recent_keywords)
            if event.keyword not in keywords:
                keywords.insert(0, event.keyword)
            profile.recent_keywords = keywords[:20]

        if event.event_type in [EventType.ORDER_CREATED, EventType.PAYMENT_SUCCESS]:
            profile.purchase_intent_score = min(100, profile.purchase_intent_score + 10)

        profile.preferred_brands = sorted(profile.preferred_brands, key=lambda x: x.score, reverse=True)
        profile.preferred_categories = sorted(profile.preferred_categories, key=lambda x: x.score, reverse=True)
        profile.preferred_price_ranges = sorted(profile.preferred_price_ranges, key=lambda x: x.score, reverse=True)
        profile.preference_score_summary = {
            "brand_count": float(len(profile.preferred_brands)),
            "category_count": float(len(profile.preferred_categories)),
            "price_range_count": float(len(profile.preferred_price_ranges)),
        }
        return profile

    @staticmethod
    def _update_brand_preferences(existing_items: List[BrandPreference], brand_name: str, score_delta: float) -> List[BrandPreference]:
        items = list(existing_items)
        existing = next((item for item in items if item.brand_name == brand_name), None)
        if existing:
            index = items.index(existing)
            items[index] = BrandPreference(
                brand_name=existing.brand_name,
                score=min(100, existing.score + score_delta),
                interaction_count=existing.interaction_count + 1,
            )
        else:
            items.append(BrandPreference(brand_name=brand_name, score=min(100, score_delta), interaction_count=1))
        return items

    @staticmethod
    def _update_category_preferences(existing_items: List[CategoryPreference], category_name: str, score_delta: float) -> List[CategoryPreference]:
        items = list(existing_items)
        existing = next((item for item in items if item.category_name == category_name), None)
        if existing:
            index = items.index(existing)
            items[index] = CategoryPreference(
                category_name=existing.category_name,
                score=min(100, existing.score + score_delta),
                interaction_count=existing.interaction_count + 1,
            )
        else:
            items.append(CategoryPreference(category_name=category_name, score=min(100, score_delta), interaction_count=1))
        return items

    @staticmethod
    def _update_price_preferences(
        existing_items: List[PriceRangePreference],
        price_range: PriceRange,
        score_delta: float,
    ) -> List[PriceRangePreference]:
        items = list(existing_items)
        existing = next((item for item in items if item.price_range == price_range), None)
        if existing:
            index = items.index(existing)
            items[index] = PriceRangePreference(
                price_range=existing.price_range,
                score=min(100, existing.score + score_delta),
                interaction_count=existing.interaction_count + 1,
            )
        else:
            items.append(PriceRangePreference(price_range=price_range, score=min(100, score_delta), interaction_count=1))
        return items


class SimpleRecommendationScorer(RecommendationScorer):
    """Profile-based baseline scorer."""

    def __init__(self, price_normalizer: Optional[PriceRangeNormalizer] = None):
        self.price_normalizer = price_normalizer or DefaultPriceRangeNormalizer()

    def score_product_for_user(
        self,
        product_id: UUID,
        product_brand: str,
        product_category: str,
        product_price: float,
        user_profile: UserPreferenceProfile,
    ) -> float:
        score = 50.0

        for brand_pref in user_profile.preferred_brands[:3]:
            if normalize_text(product_brand) == normalize_text(brand_pref.brand_name):
                score += 25.0 * (brand_pref.score / 100.0)
                break

        for cat_pref in user_profile.preferred_categories[:3]:
            if normalize_text(product_category) == normalize_text(cat_pref.category_name):
                score += 15.0 * (cat_pref.score / 100.0)
                break

        product_price_range = self.price_normalizer.normalize_price(product_price)
        for price_pref in user_profile.preferred_price_ranges[:3]:
            if product_price_range == price_pref.price_range:
                score += 10.0 * (price_pref.score / 100.0)
                break

        return min(100, max(0, score))

    def get_reason_codes(
        self,
        product_brand: str,
        product_category: str,
        product_price: float,
        user_profile: UserPreferenceProfile,
    ) -> List[str]:
        reasons = []

        if any(normalize_text(product_brand) == normalize_text(item.brand_name) for item in user_profile.preferred_brands[:3]):
            reasons.append("preferred_product_group")
        if any(normalize_text(product_category) == normalize_text(item.category_name) for item in user_profile.preferred_categories[:3]):
            reasons.append("preferred_category")

        product_price_range = self.price_normalizer.normalize_price(product_price)
        if any(product_price_range == item.price_range for item in user_profile.preferred_price_ranges[:3]):
            reasons.append("preferred_price_range")

        if not reasons:
            reasons.append("catalog_match")
        return reasons


class MockGraphService(GraphService):
    """Fallback graph service when Neo4j is unavailable."""

    def sync_event_to_graph(self, event: BehavioralEvent) -> None:
        if event.user_id and event.has_product_context():
            logger.debug("Mock graph sync for user=%s event=%s", event.user_id, event.event_type.value)

    def get_user_top_brands(self, user_id: UUID, limit: int = 5) -> List[Tuple[str, int]]:
        return []

    def get_user_top_categories(self, user_id: UUID, limit: int = 5) -> List[Tuple[str, int]]:
        return []

    def get_related_products(self, product_id: UUID, limit: int = 5) -> List[UUID]:
        return []

    def score_product_affinity(self, user_id: UUID, product: Dict[str, Any]) -> float:
        return 0.0

    def upsert_product_node(self, product: Dict[str, Any]) -> None:
        return None

    def link_similar_products(self, source_product_id: str, target_product_id: str, weight: float = 1.0, reason: str = "csv") -> None:
        return None

    def clear_graph(self) -> None:
        return None


class Neo4jGraphService(GraphService):
    """Neo4j-backed graph service for behavioral and recommendation signals."""

    EVENT_RELATIONSHIP_MAP = {
        EventType.SEARCH.value: "SEARCHED_PRODUCT",
        EventType.PRODUCT_VIEW.value: "VIEWED",
        EventType.PRODUCT_CLICK.value: "CLICKED",
        EventType.VIEW_CATEGORY.value: "VIEWED_CATEGORY",
        EventType.ADD_TO_CART.value: "ADDED_TO_CART",
        EventType.REMOVE_FROM_CART.value: "REMOVED_FROM_CART",
        EventType.ADD_TO_WISHLIST.value: "ADDED_TO_WISHLIST",
        EventType.CHECKOUT_STARTED.value: "CHECKOUT_STARTED",
        EventType.ORDER_CREATED.value: "ORDERED",
        EventType.ORDER_CANCEL.value: "CANCELLED_ORDER",
        EventType.PAYMENT_SUCCESS.value: "PAID",
        EventType.CHAT_QUERY.value: "ASKED_ABOUT",
    }

    def __init__(self, uri: Optional[str] = None, user: Optional[str] = None, password: Optional[str] = None):
        self.uri = uri or settings.NEO4J_URI
        self.user = user or settings.NEO4J_USER
        self.password = password or settings.NEO4J_PASSWORD
        self._driver = None

    @property
    def driver(self):
        if self._driver is None:
            self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        return self._driver

    def sync_event_to_graph(self, event: BehavioralEvent) -> None:
        if not event.user_id:
            return
        try:
            rel_type = self.EVENT_RELATIONSHIP_MAP.get(event.event_type.value, "INTERACTED_WITH")
            with self.driver.session() as session:
                session.execute_write(self._sync_event_tx, rel_type, event)
        except Exception as exc:
            logger.warning("Neo4j sync failed for event %s: %s", event.id, exc)

    @staticmethod
    def _sync_event_tx(tx, rel_type: str, event: BehavioralEvent) -> None:
        timestamp = event.occurred_at.isoformat() if event.occurred_at else None
        tx.run(
            f"""
            MERGE (u:User {{id: $user_id}})
            SET u.last_interaction_at = datetime($occurred_at)
            MERGE (e:Event:Behavior {{id: $event_id}})
            SET e.type = $event_type,
                e.occurred_at = datetime($occurred_at),
                e.session_id = $session_id,
                e.source_service = $source_service,
                e.keyword = $keyword,
                e.price_amount = $price_amount
            MERGE (u)-[:PERFORMED]->(e)
            FOREACH (_ IN CASE WHEN $product_id IS NULL THEN [] ELSE [1] END |
                MERGE (p:Product {{id: $product_id}})
                SET p.name = coalesce(p.name, $product_name),
                    p.product_group = coalesce($brand_name, p.product_group),
                    p.category = coalesce($category_name, p.category),
                    p.price = coalesce($price_amount, p.price),
                    p.last_seen_at = datetime($occurred_at)
                MERGE (e)-[:TARGETS]->(p)
                MERGE (u)-[r:{rel_type}]->(p)
                SET r.weight = coalesce(r.weight, 0.0) + $weight,
                    r.last_at = datetime($occurred_at),
                    r.event_type = $event_type
            )
            FOREACH (_ IN CASE WHEN $brand_name IS NULL OR trim($brand_name) = '' THEN [] ELSE [1] END |
                MERGE (g:Brand:ProductGroup {{name: $brand_name}})
                MERGE (e)-[:MENTIONS_BRAND]->(g)
                MERGE (u)-[rg:INTERESTED_IN_GROUP]->(g)
                SET rg.weight = coalesce(rg.weight, 0.0) + $weight,
                    rg.last_at = datetime($occurred_at)
            )
            FOREACH (_ IN CASE WHEN $category_name IS NULL OR trim($category_name) = '' THEN [] ELSE [1] END |
                MERGE (c:Category {{name: $category_name}})
                MERGE (e)-[:TARGETS_CATEGORY]->(c)
                MERGE (u)-[rc:INTERESTED_IN_CATEGORY]->(c)
                SET rc.weight = coalesce(rc.weight, 0.0) + $weight,
                    rc.last_at = datetime($occurred_at)
            )
            FOREACH (_ IN CASE WHEN $product_id IS NULL OR $brand_name IS NULL OR trim($brand_name) = '' THEN [] ELSE [1] END |
                MERGE (p:Product {{id: $product_id}})
                MERGE (g:Brand:ProductGroup {{name: $brand_name}})
                MERGE (p)-[:BELONGS_TO_GROUP]->(g)
            )
            FOREACH (_ IN CASE WHEN $product_id IS NULL OR $category_name IS NULL OR trim($category_name) = '' THEN [] ELSE [1] END |
                MERGE (p:Product {{id: $product_id}})
                MERGE (c:Category {{name: $category_name}})
                MERGE (p)-[:IN_CATEGORY]->(c)
            )
            FOREACH (_ IN CASE WHEN $keyword IS NULL OR trim($keyword) = '' THEN [] ELSE [1] END |
                MERGE (k:Keyword:Query {{term: $keyword}})
                MERGE (e)-[:USES_QUERY]->(k)
                MERGE (u)-[rk:SEARCHED_KEYWORD]->(k)
                SET rk.weight = coalesce(rk.weight, 0.0) + 1.0,
                    rk.last_at = datetime($occurred_at)
            )
            """,
            event_id=str(event.id),
            user_id=str(event.user_id),
            product_id=str(event.product_id) if event.product_id else None,
            product_name=event.metadata.get("product_name"),
            brand_name=event.brand_name,
            category_name=event.category_name,
            price_amount=float(event.price_amount) if event.price_amount is not None else None,
            keyword=event.keyword,
            occurred_at=timestamp,
            event_type=event.event_type.value,
            session_id=event.session_id,
            source_service=event.source_service,
            weight=float(event.get_behavior_score()),
        )

    def upsert_product_node(self, product: Dict[str, Any]) -> None:
        try:
            with self.driver.session() as session:
                session.execute_write(self._upsert_product_tx, product)
        except Exception as exc:
            logger.warning("Neo4j product upsert failed for %s: %s", product.get("id"), exc)

    @staticmethod
    def _upsert_product_tx(tx, product: Dict[str, Any]) -> None:
        product_id = str(product.get("id") or "")
        if not product_id:
            return
        tx.run(
            """
            MERGE (p:Product {id: $product_id})
            SET p.name = $name,
                p.slug = $slug,
                p.product_group = $group_name,
                p.category = $category_name,
                p.description = $description,
                p.price = $price,
                p.thumbnail_url = $thumbnail_url,
                p.is_featured = $is_featured
            FOREACH (_ IN CASE WHEN $group_name IS NULL OR trim($group_name) = '' THEN [] ELSE [1] END |
                MERGE (g:Brand:ProductGroup {name: $group_name})
                MERGE (p)-[:BELONGS_TO_GROUP]->(g)
            )
            FOREACH (_ IN CASE WHEN $category_name IS NULL OR trim($category_name) = '' THEN [] ELSE [1] END |
                MERGE (c:Category {name: $category_name})
                MERGE (p)-[:IN_CATEGORY]->(c)
            )
            """,
            product_id=product_id,
            name=product.get("name"),
            slug=product.get("slug"),
            group_name=product.get("brand_name") or product.get("brand"),
            category_name=product.get("category_name") or product.get("category"),
            description=product.get("short_description") or product.get("description"),
            price=_to_float(product.get("base_price") or product.get("price")),
            thumbnail_url=product.get("thumbnail_url"),
            is_featured=bool(product.get("is_featured", False)),
        )

    def link_similar_products(self, source_product_id: str, target_product_id: str, weight: float = 1.0, reason: str = "csv") -> None:
        try:
            with self.driver.session() as session:
                session.execute_write(
                    self._link_similar_tx,
                    source_product_id,
                    target_product_id,
                    weight,
                    reason,
                )
        except Exception as exc:
            logger.warning("Neo4j similar link failed %s -> %s: %s", source_product_id, target_product_id, exc)

    @staticmethod
    def _link_similar_tx(tx, source_product_id: str, target_product_id: str, weight: float, reason: str) -> None:
        tx.run(
            """
            MATCH (source:Product {id: $source_product_id})
            MATCH (target:Product {id: $target_product_id})
            MERGE (source)-[r:SIMILAR]->(target)
            SET r.weight = $weight, r.reason = $reason
            MERGE (target)-[r2:SIMILAR]->(source)
            SET r2.weight = $weight, r2.reason = $reason
            """,
            source_product_id=source_product_id,
            target_product_id=target_product_id,
            weight=float(weight),
            reason=reason,
        )

    def clear_graph(self) -> None:
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

    def get_user_top_brands(self, user_id: UUID, limit: int = 5) -> List[Tuple[str, int]]:
        query = """
        MATCH (u:User {id: $user_id})
        CALL {
            WITH u
            MATCH (u)-[direct:INTERESTED_IN_GROUP]->(g:ProductGroup)
            RETURN g.name AS label, coalesce(direct.weight, 0.0) AS weight
            UNION ALL
            WITH u
            MATCH (u)-[r]->(:Product)-[:BELONGS_TO_GROUP]->(pg:ProductGroup)
            RETURN pg.name AS label, coalesce(r.weight, 0.0) AS weight
        }
        WITH label, weight WHERE label IS NOT NULL
        RETURN label, toInteger(sum(weight)) AS score
        ORDER BY score DESC, label ASC
        LIMIT $limit
        """
        return self._run_top_query(query, user_id, limit)

    def get_user_top_categories(self, user_id: UUID, limit: int = 5) -> List[Tuple[str, int]]:
        query = """
        MATCH (u:User {id: $user_id})
        CALL {
            WITH u
            MATCH (u)-[direct:INTERESTED_IN_CATEGORY]->(c:Category)
            RETURN c.name AS label, coalesce(direct.weight, 0.0) AS weight
            UNION ALL
            WITH u
            MATCH (u)-[r]->(:Product)-[:IN_CATEGORY]->(pc:Category)
            RETURN pc.name AS label, coalesce(r.weight, 0.0) AS weight
        }
        WITH label, weight WHERE label IS NOT NULL
        RETURN label, toInteger(sum(weight)) AS score
        ORDER BY score DESC, label ASC
        LIMIT $limit
        """
        return self._run_top_query(query, user_id, limit)

    def _run_top_query(self, query: str, user_id: UUID, limit: int) -> List[Tuple[str, int]]:
        try:
            with self.driver.session() as session:
                records = session.run(query, user_id=str(user_id), limit=limit)
                return [(record["label"], int(record["score"])) for record in records if record["label"]]
        except Exception as exc:
            logger.warning("Neo4j top-query failed for user %s: %s", user_id, exc)
            return []

    def get_related_products(self, product_id: UUID, limit: int = 5) -> List[UUID]:
        try:
            with self.driver.session() as session:
                records = session.run(
                    """
                    MATCH (:Product {id: $product_id})-[r:SIMILAR]->(rec:Product)
                    RETURN rec.id AS product_id
                    ORDER BY coalesce(r.weight, 1.0) DESC, rec.name ASC
                    LIMIT $limit
                    """,
                    product_id=str(product_id),
                    limit=limit,
                )
                return [UUID(record["product_id"]) for record in records]
        except Exception as exc:
            logger.warning("Neo4j related-products query failed for %s: %s", product_id, exc)
            return []

    def score_product_affinity(self, user_id: UUID, product: Dict[str, Any]) -> float:
        product_id = str(product.get("id") or "")
        group_name = product.get("brand_name") or product.get("brand") or ""
        category_name = product.get("category_name") or product.get("category") or ""
        if not (product_id or group_name or category_name):
            return 0.0

        try:
            with self.driver.session() as session:
                record = session.run(
                    """
                    MATCH (u:User {id: $user_id})
                    OPTIONAL MATCH (u)-[direct]->(candidate:Product {id: $product_id})
                    WITH u, sum(coalesce(direct.weight, 0.0)) AS direct_product_score
                    OPTIONAL MATCH (u)-[seen_rel]->(seen:Product)-[sim:SIMILAR]->(:Product {id: $product_id})
                    WITH u, direct_product_score, sum(coalesce(seen_rel.weight, 0.0) * coalesce(sim.weight, 0.0)) AS related_product_score
                    OPTIONAL MATCH (u)-[group_rel:INTERESTED_IN_GROUP]->(:ProductGroup {name: $group_name})
                    WITH u, direct_product_score, related_product_score, sum(coalesce(group_rel.weight, 0.0)) AS direct_group_score
                    OPTIONAL MATCH (u)-[product_group_rel]->(:Product)-[:BELONGS_TO_GROUP]->(:ProductGroup {name: $group_name})
                    WITH u, direct_product_score, related_product_score, direct_group_score, sum(coalesce(product_group_rel.weight, 0.0)) AS implicit_group_score
                    OPTIONAL MATCH (u)-[category_rel:INTERESTED_IN_CATEGORY]->(:Category {name: $category_name})
                    WITH u, direct_product_score, related_product_score, direct_group_score, implicit_group_score, sum(coalesce(category_rel.weight, 0.0)) AS direct_category_score
                    OPTIONAL MATCH (u)-[product_category_rel]->(:Product)-[:IN_CATEGORY]->(:Category {name: $category_name})
                    RETURN direct_product_score,
                           related_product_score,
                           direct_group_score,
                           implicit_group_score,
                           direct_category_score,
                           sum(coalesce(product_category_rel.weight, 0.0)) AS implicit_category_score
                    """,
                    user_id=str(user_id),
                    product_id=product_id,
                    group_name=group_name,
                    category_name=category_name,
                ).single()
        except Exception as exc:
            logger.warning("Neo4j affinity scoring failed for user=%s product=%s: %s", user_id, product_id, exc)
            return 0.0

        if not record:
            return 0.0

        total = (
            float(record["direct_product_score"] or 0.0) * 1.6
            + float(record["related_product_score"] or 0.0) * 1.2
            + float(record["direct_group_score"] or 0.0)
            + float(record["implicit_group_score"] or 0.0) * 0.7
            + float(record["direct_category_score"] or 0.0)
            + float(record["implicit_category_score"] or 0.0) * 0.7
        )
        return min(1.0, total / 25.0)


class SimpleRetrievalService(RetrievalService):
    """Keyword-first retrieval service with semantic overlap scoring."""

    STOP_WORDS = {
        "toi", "tôi", "can", "cần", "muon", "muốn", "tim", "tìm", "cho", "gia", "giá",
        "loai", "loại", "san", "pham", "sản", "phẩm", "cua", "cửa", "hang", "hãng", "nhom",
        "product", "nao", "nào", "phu", "hop", "phù", "hợp",
    }

    def __init__(self):
        self.chunk_repo = DjangoKnowledgeChunkRepository()

    def retrieve_relevant_chunks(
        self,
        query: str,
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[KnowledgeChunk]:
        chunks = self.chunk_repo.search_similar(query, limit=limit * 4)
        ranked = sorted(
            chunks,
            key=lambda chunk: self.score_query_to_text(query, chunk.content, metadata=chunk.metadata),
            reverse=True,
        )
        return ranked[:limit]

    def retrieve_by_type(self, query: str, document_type: str, limit: int = 5) -> List[KnowledgeChunk]:
        chunks = self.chunk_repo.search_similar(query, limit=limit * 4)
        filtered = [
            chunk for chunk in chunks
            if chunk.metadata.get("document_type") == document_type
        ]
        ranked = sorted(
            filtered,
            key=lambda chunk: self.score_query_to_text(query, chunk.content, metadata=chunk.metadata),
            reverse=True,
        )
        return ranked[:limit]

    def score_query_to_text(self, query: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> float:
        query_tokens = [token for token in tokenize(query) if token not in self.STOP_WORDS]
        if not query_tokens:
            return 0.0

        text_tokens = set(tokenize(text))
        if metadata:
            text_tokens.update(tokenize(" ".join(str(value) for value in metadata.values())))

        overlap = sum(1 for token in query_tokens if token in text_tokens)
        return overlap / max(len(set(query_tokens)), 1)

    def score_product_match(self, query: str, product: Dict[str, Any]) -> float:
        searchable = " ".join(
            str(product.get(key, ""))
            for key in ("name", "brand_name", "brand", "category_name", "category", "short_description", "description")
        )
        metadata = {"tags": product.get("attributes", {})}
        return self.score_query_to_text(query, searchable, metadata=metadata)


def get_graph_service() -> GraphService:
    """Return Neo4j graph service with graceful fallback."""
    try:
        return Neo4jGraphService()
    except Exception as exc:
        logger.warning("Falling back to mock graph service: %s", exc)
        return MockGraphService()


def get_sequence_service() -> SequenceRecommendationService:
    """Return sequence scoring service bound to configured artifact paths."""
    return SequenceRecommendationService(
        model_path=Path(settings.LSTM_MODEL_PATH),
        metadata_path=Path(settings.LSTM_METADATA_PATH),
    )


def _to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
