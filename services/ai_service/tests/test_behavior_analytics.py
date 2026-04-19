from modules.ai.application.services import BehaviorAnalyticsUseCase


def test_get_funnel_with_empty_event_list_does_not_hit_database(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("database loader should not run for an explicit empty list")

    monkeypatch.setattr(BehaviorAnalyticsUseCase, "_load_events", boom)

    result = BehaviorAnalyticsUseCase().get_funnel([])

    assert result == {
        "search_sessions": 0,
        "view_sessions": 0,
        "cart_sessions": 0,
        "checkout_sessions": 0,
        "order_sessions": 0,
        "payment_success_sessions": 0,
    }
