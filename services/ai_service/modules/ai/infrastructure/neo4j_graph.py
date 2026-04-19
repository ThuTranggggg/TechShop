"""Neo4j graph access for AI service and offline KB_Graph imports."""

from __future__ import annotations

import logging
import os
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from uuid import UUID

from django.conf import settings as django_settings
from neo4j import GraphDatabase

from modules.ai.domain.entities import BehavioralEvent
from modules.ai.domain.services import GraphService

logger = logging.getLogger(__name__)

ACTION_RELATIONSHIPS = {
    "view": "VIEWED",
    "click": "CLICKED",
    "add_to_cart": "ADDED_TO_CART",
    "search": "SEARCHED",
    "product_view": "VIEWED",
    "product_click": "CLICKED",
}

PRICE_BUCKETS: Sequence[Tuple[float, float, str]] = (
    (0, 1_000_000, "under_1m"),
    (1_000_000, 3_000_000, "from_1m_to_3m"),
    (3_000_000, 5_000_000, "from_3m_to_5m"),
    (5_000_000, 10_000_000, "from_5m_to_10m"),
    (10_000_000, 20_000_000, "from_10m_to_20m"),
    (20_000_000, float("inf"), "above_20m"),
)


def price_bucket(amount: float) -> str:
    """Map a price to the same buckets used by the report narrative."""
    for minimum, maximum, bucket in PRICE_BUCKETS:
        if minimum <= amount < maximum:
            return bucket
    return "above_20m"


def normalize_timestamp(value: Any) -> str:
    """Neo4j accepts ISO-8601 strings and the import script already keeps UTC."""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


@dataclass(frozen=True)
class GraphRecord:
    """Normalized row passed into Neo4j imports."""

    user_id: str
    product_id: str
    action: str
    timestamp: str
    product_name: str = ""
    brand_name: str = ""
    category_name: str = ""
    price_amount: float = 0.0
    behavior_profile: str = "unclassified"


class Neo4jGraphService(GraphService):
    """Real graph owner so event sync and report imports hit the same schema."""

    def __init__(
        self,
        *,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        if django_settings.configured:
            self.uri = uri or django_settings.NEO4J_URI
            self.user = user or django_settings.NEO4J_USER
            self.password = password or django_settings.NEO4J_PASSWORD
        else:
            self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
            self.user = user or os.getenv("NEO4J_USER", "neo4j")
            self.password = password or os.getenv("NEO4J_PASSWORD", "neo4jpassword")
        if not self.uri or not self.user or not self.password:
            raise RuntimeError("Neo4j graph configuration is incomplete")
        self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        self._schema_ready = False

    def close(self) -> None:
        if self._driver:
            self._driver.close()

    def __enter__(self) -> "Neo4jGraphService":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _session(self):
        return self._driver.session()

    def _ensure_schema(self) -> None:
        if self._schema_ready:
            return

        statements = [
            "CREATE CONSTRAINT user_user_id IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE",
            "CREATE CONSTRAINT product_product_id IF NOT EXISTS FOR (p:Product) REQUIRE p.product_id IS UNIQUE",
            "CREATE CONSTRAINT brand_name IF NOT EXISTS FOR (b:Brand) REQUIRE b.name IS UNIQUE",
            "CREATE CONSTRAINT category_name IF NOT EXISTS FOR (c:Category) REQUIRE c.name IS UNIQUE",
            "CREATE CONSTRAINT behavior_profile_name IF NOT EXISTS FOR (b:BehaviorProfile) REQUIRE b.name IS UNIQUE",
        ]
        with self._session() as session:
            for statement in statements:
                session.run(statement)
        self._schema_ready = True

    def _run_query(self, cypher: str, **params: Any) -> List[Dict[str, Any]]:
        with self._session() as session:
            result = session.run(cypher, **params)
            return [record.data() for record in result]

    def sync_event_to_graph(self, event: BehavioralEvent) -> None:
        self._ensure_schema()
        relationship = ACTION_RELATIONSHIPS.get(event.event_type.value)
        if not relationship:
            return

        if event.event_type.value == "search":
            if not (event.user_id and event.keyword):
                return
            params = {
                "user_id": str(event.user_id),
                "keyword": event.keyword,
                "timestamp": normalize_timestamp(event.occurred_at or event.created_at),
                "behavior_profile": event.metadata.get("behavior_profile", "unclassified"),
            }
            cypher = """
            MERGE (u:User {user_id: $user_id})
            MERGE (s:SearchTerm {keyword: $keyword})
            MERGE (profile:BehaviorProfile {name: $behavior_profile})
            MERGE (u)-[:EXHIBITS]->(profile)
            MERGE (u)-[r:SEARCHED]->(s)
            SET r.last_seen_at = datetime($timestamp),
                r.count = coalesce(r.count, 0) + 1
            """
            self._run_query(cypher, **params)
            return

        if not (event.user_id and event.product_id):
            return

        params = {
            "user_id": str(event.user_id),
            "product_id": str(event.product_id),
            "action": event.event_type.value,
            "timestamp": normalize_timestamp(event.occurred_at or event.created_at),
            "brand_name": event.brand_name or "",
            "category_name": event.category_name or "",
            "price_amount": float(event.price_amount or 0.0),
            "behavior_profile": event.metadata.get("behavior_profile", "unclassified"),
        }
        cypher = f"""
        MERGE (u:User {{user_id: $user_id}})
        MERGE (p:Product {{product_id: $product_id}})
        SET p.brand_name = coalesce($brand_name, p.brand_name),
            p.category_name = coalesce($category_name, p.category_name),
            p.price_amount = coalesce($price_amount, p.price_amount),
            p.price_bucket = CASE
                WHEN $price_amount < 1000000 THEN 'under_1m'
                WHEN $price_amount < 3000000 THEN 'from_1m_to_3m'
                WHEN $price_amount < 5000000 THEN 'from_3m_to_5m'
                WHEN $price_amount < 10000000 THEN 'from_5m_to_10m'
                WHEN $price_amount < 20000000 THEN 'from_10m_to_20m'
                ELSE 'above_20m'
            END
        MERGE (brand:Brand {{name: coalesce($brand_name, 'Unknown')}})
        MERGE (category:Category {{name: coalesce($category_name, 'Unknown')}})
        MERGE (profile:BehaviorProfile {{name: $behavior_profile}})
        MERGE (u)-[:EXHIBITS]->(profile)
        MERGE (p)-[:IN_BRAND]->(brand)
        MERGE (p)-[:IN_CATEGORY]->(category)
        MERGE (u)-[r:{relationship}]->(p)
        SET r.last_seen_at = datetime($timestamp),
            r.count = coalesce(r.count, 0) + 1,
            r.action = $action
        """
        self._run_query(cypher, **params)

    def seed_from_rows(self, rows: Iterable[GraphRecord]) -> Dict[str, int]:
        """Import a whole CSV snapshot; the offline assignment uses this to build KB_Graph."""
        self._ensure_schema()
        grouped: Dict[str, List[GraphRecord]] = defaultdict(list)
        counts = {"rows": 0, "users": set(), "products": set(), "profiles": set()}
        for row in rows:
            grouped[row.action].append(row)
            counts["rows"] += 1
            counts["users"].add(row.user_id)
            counts["products"].add(row.product_id)
            counts["profiles"].add(row.behavior_profile)

        for action, batch in grouped.items():
            relationship = ACTION_RELATIONSHIPS.get(action)
            if not relationship:
                continue
            cypher = f"""
            UNWIND $rows AS row
            MERGE (u:User {{user_id: row.user_id}})
            MERGE (p:Product {{product_id: row.product_id}})
            SET p.name = coalesce(row.product_name, p.name),
                p.brand_name = coalesce(row.brand_name, p.brand_name),
                p.category_name = coalesce(row.category_name, p.category_name),
                p.price_amount = coalesce(row.price_amount, p.price_amount),
                p.price_bucket = coalesce(row.price_bucket, p.price_bucket)
            MERGE (brand:Brand {{name: coalesce(row.brand_name, 'Unknown')}})
            MERGE (category:Category {{name: coalesce(row.category_name, 'Unknown')}})
            MERGE (profile:BehaviorProfile {{name: coalesce(row.behavior_profile, 'unclassified')}})
            MERGE (u)-[:EXHIBITS]->(profile)
            MERGE (p)-[:IN_BRAND]->(brand)
            MERGE (p)-[:IN_CATEGORY]->(category)
            MERGE (u)-[r:{relationship}]->(p)
            SET r.last_seen_at = datetime(row.timestamp),
                r.count = coalesce(r.count, 0) + 1,
                r.action = row.action
            """
            payload = [
                {
                    "user_id": row.user_id,
                    "product_id": row.product_id,
                    "action": row.action,
                    "timestamp": row.timestamp,
                    "product_name": row.product_name,
                    "brand_name": row.brand_name,
                    "category_name": row.category_name,
                    "price_amount": row.price_amount,
                    "price_bucket": price_bucket(row.price_amount),
                    "behavior_profile": row.behavior_profile,
                }
                for row in batch
            ]
            self._run_query(cypher, rows=payload)

        return {
            "rows": counts["rows"],
            "users": len(counts["users"]),
            "products": len(counts["products"]),
            "profiles": len(counts["profiles"]),
        }

    def get_user_top_brands(self, user_id: UUID, limit: int = 5) -> List[Tuple[str, int]]:
        query = """
        MATCH (u:User {user_id: $user_id})-[r:VIEWED|CLICKED|ADDED_TO_CART]->(:Product)-[:IN_BRAND]->(b:Brand)
        RETURN b.name AS brand_name, count(r) AS count
        ORDER BY count DESC, brand_name ASC
        LIMIT $limit
        """
        rows = self._run_query(query, user_id=str(user_id), limit=limit)
        return [(row["brand_name"], int(row["count"])) for row in rows]

    def get_user_top_categories(self, user_id: UUID, limit: int = 5) -> List[Tuple[str, int]]:
        query = """
        MATCH (u:User {user_id: $user_id})-[r:VIEWED|CLICKED|ADDED_TO_CART]->(:Product)-[:IN_CATEGORY]->(c:Category)
        RETURN c.name AS category_name, count(r) AS count
        ORDER BY count DESC, category_name ASC
        LIMIT $limit
        """
        rows = self._run_query(query, user_id=str(user_id), limit=limit)
        return [(row["category_name"], int(row["count"])) for row in rows]

    def get_user_top_price_ranges(self, user_id: UUID, limit: int = 5) -> List[Tuple[str, int]]:
        query = """
        MATCH (u:User {user_id: $user_id})-[r:VIEWED|CLICKED|ADDED_TO_CART]->(p:Product)
        RETURN coalesce(p.price_bucket, 'unknown') AS price_bucket, count(r) AS count
        ORDER BY count DESC, price_bucket ASC
        LIMIT $limit
        """
        rows = self._run_query(query, user_id=str(user_id), limit=limit)
        return [(row["price_bucket"], int(row["count"])) for row in rows]

    def get_related_products(self, product_id: UUID, limit: int = 5) -> List[UUID]:
        query = """
        MATCH (p:Product {product_id: $product_id})<-[:VIEWED|CLICKED|ADDED_TO_CART]-(u:User)
              -[r:VIEWED|CLICKED|ADDED_TO_CART]->(related:Product)
        WHERE related.product_id <> $product_id
        RETURN related.product_id AS product_id, count(r) AS score
        ORDER BY score DESC, product_id ASC
        LIMIT $limit
        """
        rows = self._run_query(query, product_id=str(product_id), limit=limit)
        return [UUID(row["product_id"]) for row in rows]
