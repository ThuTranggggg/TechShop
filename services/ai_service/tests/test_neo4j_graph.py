from uuid import UUID, uuid4

from modules.ai.domain.entities import BehavioralEvent
from modules.ai.domain.value_objects import EventType
from modules.ai.infrastructure import neo4j_graph
from modules.ai.infrastructure.neo4j_graph import GraphRecord, Neo4jGraphService


class FakeRecord(dict):
    def data(self):
        return dict(self)


class FakeSession:
    def __init__(self, records=None):
        self.records = records or []
        self.queries = []

    def run(self, query, **params):
        self.queries.append((query, params))
        return [FakeRecord(record) for record in self.records]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeDriver:
    def __init__(self, records=None):
        self.session_obj = FakeSession(records=records)

    def session(self):
        return self.session_obj

    def close(self):
        return None


def test_sync_event_to_graph_uses_action_relationship(monkeypatch):
    fake_driver = FakeDriver()
    monkeypatch.setattr(neo4j_graph.GraphDatabase, "driver", lambda *args, **kwargs: fake_driver)

    service = Neo4jGraphService(uri="bolt://example", user="neo4j", password="secret")
    event = BehavioralEvent(
        id=uuid4(),
        event_type=EventType.PRODUCT_CLICK,
        user_id=uuid4(),
        product_id=uuid4(),
        brand_name="Samsung",
        category_name="Phone",
        price_amount=9_990_000,
    )

    service.sync_event_to_graph(event)

    cypher_queries = [query for query, _ in fake_driver.session_obj.queries]
    assert any("MERGE (u:User" in query for query in cypher_queries)
    assert any("CLICKED" in query for query in cypher_queries)


def test_seed_from_rows_groups_records_and_returns_counts(monkeypatch):
    fake_driver = FakeDriver()
    monkeypatch.setattr(neo4j_graph.GraphDatabase, "driver", lambda *args, **kwargs: fake_driver)

    service = Neo4jGraphService(uri="bolt://example", user="neo4j", password="secret")
    rows = [
        GraphRecord(
            user_id=str(UUID(int=1)),
            product_id=str(UUID(int=2)),
            action="view",
            timestamp="2026-01-01T00:00:00Z",
            product_name="Galaxy",
            brand_name="Samsung",
            category_name="Phone",
            price_amount=9_990_000,
            behavior_profile="window_shopper",
        ),
        GraphRecord(
            user_id=str(UUID(int=1)),
            product_id=str(UUID(int=3)),
            action="add_to_cart",
            timestamp="2026-01-01T00:05:00Z",
            product_name="Galaxy Buds",
            brand_name="Samsung",
            category_name="Audio",
            price_amount=4_990_000,
            behavior_profile="window_shopper",
        ),
    ]

    summary = service.seed_from_rows(rows)

    assert summary == {"rows": 2, "users": 1, "products": 2, "profiles": 1}
    cypher_queries = [query for query, _ in fake_driver.session_obj.queries]
    assert any("VIEWED" in query for query in cypher_queries)
    assert any("ADDED_TO_CART" in query for query in cypher_queries)


def test_sync_search_event_uses_search_term_nodes(monkeypatch):
    fake_driver = FakeDriver()
    monkeypatch.setattr(neo4j_graph.GraphDatabase, "driver", lambda *args, **kwargs: fake_driver)

    service = Neo4jGraphService(uri="bolt://example", user="neo4j", password="secret")
    event = BehavioralEvent(
        id=uuid4(),
        event_type=EventType.SEARCH,
        user_id=uuid4(),
        keyword="laptop gaming",
    )

    service.sync_event_to_graph(event)

    cypher_queries = [query for query, _ in fake_driver.session_obj.queries]
    assert any("SearchTerm" in query for query in cypher_queries)
    assert any("SEARCHED" in query for query in cypher_queries)
