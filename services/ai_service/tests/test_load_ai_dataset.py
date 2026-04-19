from io import StringIO
from pathlib import Path
from uuid import uuid4

import modules.ai.management.commands.load_ai_dataset as load_ai_dataset
from modules.ai.management.commands.load_ai_dataset import Command


class FakeTracker:
    def __init__(self):
        self.calls = []

    def execute(self, **kwargs):
        event_type = kwargs["event_type"]
        if event_type not in {"product_view", "product_click", "add_to_cart"}:
            raise AssertionError(f"unexpected event_type: {event_type}")
        self.calls.append(kwargs)
        return kwargs


class FakeCountQuery:
    def count(self):
        return 3


def test_load_behavior_events_normalizes_legacy_actions(monkeypatch):
    user_id = str(uuid4())
    product_id = str(uuid4())
    rows = [
        {
            "user_id": user_id,
            "product_id": product_id,
            "action": "view",
            "timestamp": "2026-01-01T00:00:00Z",
        },
        {
            "user_id": user_id,
            "product_id": product_id,
            "action": "click",
            "timestamp": "2026-01-01T00:01:00Z",
        },
        {
            "user_id": user_id,
            "product_id": product_id,
            "action": "add_to_cart",
            "timestamp": "2026-01-01T00:02:00Z",
        },
    ]

    tracker = FakeTracker()

    monkeypatch.setattr(load_ai_dataset, "TrackBehavioralEventUseCase", lambda: tracker)
    monkeypatch.setattr(Command, "_load_csv", lambda self, path: rows)
    monkeypatch.setattr(load_ai_dataset.BehavioralEventModel.objects, "filter", lambda *args, **kwargs: FakeCountQuery())

    command = Command()
    command.stdout = StringIO()

    imported_users = command._load_behavior_events(Path("/tmp/data_user500.csv"), slug_mapping={})

    assert imported_users == [user_id]
    assert [call["event_type"] for call in tracker.calls] == [
        "product_view",
        "product_click",
        "add_to_cart",
    ]
