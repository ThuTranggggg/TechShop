from pathlib import Path

import modules.ai.infrastructure.sequence_models as sequence_models
from modules.ai.infrastructure.sequence_models import load_histories_from_csv, train_lstm_model


def test_load_histories_from_csv_accepts_assignment_actions(tmp_path):
    dataset_path = tmp_path / "data_user500.csv"
    dataset_path.write_text(
        "user_id,product_id,action,timestamp\n"
        "user-1,product-1,view,2026-01-01T00:00:00Z\n"
        "user-1,product-2,click,2026-01-01T00:01:00Z\n"
        "user-1,product-3,add_to_cart,2026-01-01T00:02:00Z\n"
        "user-2,product-9,ignored,2026-01-01T00:03:00Z\n",
        encoding="utf-8",
    )

    histories = load_histories_from_csv(dataset_path)

    assert histories == [("user-1", ["product-1", "product-2", "product-3"])]


def test_train_lstm_model_builds_transition_metadata_from_assignment_actions(tmp_path, monkeypatch):
    dataset_path = tmp_path / "data_user500.csv"
    dataset_path.write_text(
        "user_id,product_id,action,timestamp\n"
        "user-1,product-1,view,2026-01-01T00:00:00Z\n"
        "user-1,product-2,click,2026-01-01T00:01:00Z\n"
        "user-1,product-3,add_to_cart,2026-01-01T00:02:00Z\n",
        encoding="utf-8",
    )
    model_path = tmp_path / "model.pt"
    metadata_path = tmp_path / "metadata.json"

    monkeypatch.setattr(sequence_models, "torch", None)

    metadata = train_lstm_model(
        dataset_path=dataset_path,
        model_path=model_path,
        metadata_path=metadata_path,
        sequence_length=2,
    )

    assert metadata["sample_count"] == 2
    assert metadata["transition_scores"]["product-1"]["product-2"] == 1.0
    assert metadata["transition_scores"]["product-2"]["product-3"] == 1.0
    assert metadata_path.exists()
