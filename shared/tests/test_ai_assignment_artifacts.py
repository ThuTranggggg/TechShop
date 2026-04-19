from __future__ import annotations

import csv
import json
from pathlib import Path


ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "generated" / "ai_assignment"


def test_assignment_dataset_has_expected_shape():
    with (ARTIFACT_DIR / "data_user500.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 23109
    assert len({row["user_id"] for row in rows}) == 500
    assert sorted({row["action"] for row in rows}) == ["add_to_cart", "click", "view"]


def test_assignment_training_outputs_cover_three_models():
    training = json.loads((ARTIFACT_DIR / "training_results.json").read_text(encoding="utf-8"))

    assert set(training["models"]) == {"rnn", "lstm", "bilstm"}
    assert training["best_model"]["name"] in training["models"]
    assert training["best_model"]["artifact"].endswith("model_best.pt")
    assert training["best_model"]["comparison"]["lstm"] >= training["best_model"]["comparison"]["rnn"]


def test_assignment_graph_summary_has_expected_counts():
    summary = json.loads((ARTIFACT_DIR / "kb_graph_summary.json").read_text(encoding="utf-8"))

    assert summary["rows"] == 23109
    assert summary["users"] == 500
    assert summary["products"] == 24
    assert summary["profiles"] == 8
    assert "neo4j_import" in summary


def test_assignment_report_contains_required_sections():
    report = (ARTIFACT_DIR / "aiservice02_report.md").read_text(encoding="utf-8")

    required_sections = [
        "## 1. Trang bìa",
        "## 2. Mô tả AISERVICE",
        "## 3. Copy 20 dòng data",
        "## 4. Câu 2a: RNN, LSTM, biLSTM",
        "## 5. KB_Graph",
        "## 6. Câu 2c và 2d: RAG + e-commerce integration",
    ]

    for heading in required_sections:
        assert heading in report
