"""
Sequence-model helpers for next-product prediction.
"""
from __future__ import annotations

import csv
import json
import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from uuid import UUID

from modules.ai.domain.entities import BehavioralEvent
from modules.ai.domain.value_objects import EventType
from modules.ai.infrastructure.taxonomy import normalize_behavior_action

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
except Exception:  # pragma: no cover - optional dependency
    torch = None
    nn = None
    DataLoader = None
    TensorDataset = None


SEQUENCE_EVENT_TYPES = {
    EventType.PRODUCT_VIEW.value,
    EventType.PRODUCT_CLICK.value,
    EventType.ADD_TO_CART.value,
    EventType.CHECKOUT_STARTED.value,
    EventType.ORDER_CREATED.value,
    EventType.PAYMENT_SUCCESS.value,
}


class LSTMNextProductModel(nn.Module if nn else object):
    """Simple LSTM model for next-product prediction."""

    def __init__(self, vocab_size: int, embedding_dim: int = 32, hidden_dim: int = 64):
        if not nn:  # pragma: no cover - guarded by torch availability
            raise RuntimeError("torch is required to initialize LSTMNextProductModel")
        super().__init__()
        self.embedding = nn.Embedding(vocab_size + 1, embedding_dim, padding_idx=0)
        self.lstm = nn.LSTM(embedding_dim, hidden_dim, batch_first=True)
        self.fc = nn.Linear(hidden_dim, vocab_size + 1)

    def forward(self, x):
        embedded = self.embedding(x)
        out, _ = self.lstm(embedded)
        out = out[:, -1, :]
        return self.fc(out)


class SequenceRecommendationService:
    """Score candidate products using trained LSTM or transition fallback."""

    def __init__(self, model_path: Path, metadata_path: Path):
        self.model_path = Path(model_path)
        self.metadata_path = Path(metadata_path)
        self._metadata: Optional[Dict[str, object]] = None
        self._model = None

    @property
    def metadata(self) -> Dict[str, object]:
        if self._metadata is None:
            if self.metadata_path.exists():
                self._metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            else:
                self._metadata = {}
        return self._metadata

    def is_ready(self) -> bool:
        return bool(self.metadata)

    def score_product_for_user(
        self,
        user_id: UUID,
        candidate_product_id: str,
        recent_events: Sequence[BehavioralEvent],
    ) -> float:
        """Return a normalized 0..1 score for a candidate product."""
        recent_product_ids = [
            str(event.product_id)
            for event in recent_events
            if event.product_id and event.event_type.value in SEQUENCE_EVENT_TYPES
        ]
        if not recent_product_ids:
            return 0.0

        torch_score = self._predict_with_torch(candidate_product_id, recent_product_ids)
        if torch_score is not None:
            return torch_score

        return self._predict_with_transition_matrix(candidate_product_id, recent_product_ids)

    def _predict_with_torch(self, candidate_product_id: str, recent_product_ids: Sequence[str]) -> Optional[float]:
        if not (torch and self.model_path.exists() and self.metadata):
            return None

        product_to_index = self.metadata.get("product_to_index") or {}
        if candidate_product_id not in product_to_index:
            return 0.0

        sequence_length = int(self.metadata.get("sequence_length", 5))
        encoded = [int(product_to_index.get(product_id, 0)) for product_id in recent_product_ids[-sequence_length:]]
        if not any(encoded):
            return 0.0

        padded = [0] * max(sequence_length - len(encoded), 0) + encoded[-sequence_length:]
        model = self._load_model(len(product_to_index))
        if model is None:
            return None

        tensor = torch.tensor([padded], dtype=torch.long)
        with torch.no_grad():
            logits = model(tensor)
            probs = torch.softmax(logits, dim=-1)[0]
        index = int(product_to_index[candidate_product_id])
        return float(probs[index].item())

    def _load_model(self, vocab_size: int):
        if self._model is not None:
            return self._model
        if not (torch and self.model_path.exists()):
            return None
        model = LSTMNextProductModel(vocab_size=vocab_size)
        model.load_state_dict(torch.load(self.model_path, map_location="cpu"))
        model.eval()
        self._model = model
        return model

    def _predict_with_transition_matrix(self, candidate_product_id: str, recent_product_ids: Sequence[str]) -> float:
        transitions = self.metadata.get("transition_scores") or {}
        if not transitions:
            return 0.0

        anchor = recent_product_ids[-1]
        anchor_scores = transitions.get(anchor) or {}
        if candidate_product_id in anchor_scores:
            return float(anchor_scores[candidate_product_id])

        aggregate = 0.0
        divisor = 0
        for product_id in recent_product_ids[-3:]:
            scores = transitions.get(product_id) or {}
            if candidate_product_id in scores:
                aggregate += float(scores[candidate_product_id])
                divisor += 1
        return aggregate / divisor if divisor else 0.0


def build_training_examples(
    rows: Sequence[Tuple[str, List[str]]],
    sequence_length: int,
) -> Tuple[List[List[int]], List[int], Dict[str, int]]:
    """Build encoded training samples from user histories."""
    product_ids = sorted({product_id for _, history in rows for product_id in history})
    product_to_index = {product_id: idx + 1 for idx, product_id in enumerate(product_ids)}

    features: List[List[int]] = []
    labels: List[int] = []
    for _, history in rows:
        encoded_history = [product_to_index[product_id] for product_id in history if product_id in product_to_index]
        for idx in range(1, len(encoded_history)):
            start = max(0, idx - sequence_length)
            sequence = encoded_history[start:idx]
            padded = [0] * (sequence_length - len(sequence)) + sequence
            features.append(padded)
            labels.append(encoded_history[idx])
    return features, labels, product_to_index


def load_histories_from_csv(dataset_path: Path) -> List[Tuple[str, List[str]]]:
    """Load ordered product histories from behavior CSV."""
    histories: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    with Path(dataset_path).open("r", encoding="utf-8-sig", newline="") as file_obj:
        reader = csv.DictReader(file_obj)
        for row in reader:
            action = normalize_behavior_action((row.get("action") or row.get("event_type") or "").strip())
            if action not in SEQUENCE_EVENT_TYPES:
                continue
            user_id = (row.get("user_id") or "").strip()
            product_id = (row.get("resolved_product_id") or row.get("product_id") or row.get("product_slug") or "").strip()
            timestamp = (row.get("timestamp") or row.get("occurred_at") or "").strip()
            if user_id and product_id and timestamp:
                histories[user_id].append((timestamp, product_id))

    ordered: List[Tuple[str, List[str]]] = []
    for user_id, items in histories.items():
        items.sort(key=lambda item: item[0])
        ordered.append((user_id, [product_id for _, product_id in items]))
    return ordered


def build_transition_scores(rows: Sequence[Tuple[str, List[str]]]) -> Dict[str, Dict[str, float]]:
    """Build simple transition probabilities for fallback scoring."""
    counters: Dict[str, Counter] = defaultdict(Counter)
    for _, history in rows:
        for source, target in zip(history, history[1:]):
            counters[source][target] += 1

    scores: Dict[str, Dict[str, float]] = {}
    for source, counter in counters.items():
        total = sum(counter.values())
        scores[source] = {
            target: round(count / total, 6)
            for target, count in counter.items()
        }
    return scores


def train_lstm_model(
    dataset_path: Path,
    model_path: Path,
    metadata_path: Path,
    sequence_length: int = 5,
    epochs: int = 8,
    batch_size: int = 16,
) -> Dict[str, object]:
    """Train a compact LSTM model and persist metadata."""
    rows = load_histories_from_csv(dataset_path)
    transition_scores = build_transition_scores(rows)
    features, labels, product_to_index = build_training_examples(rows, sequence_length=sequence_length)

    metadata: Dict[str, object] = {
        "dataset_path": str(dataset_path),
        "sequence_length": sequence_length,
        "product_to_index": product_to_index,
        "transition_scores": transition_scores,
        "sample_count": len(features),
        "model_type": "transition_fallback",
    }

    if not torch or not features or not labels:
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        logger.warning("Torch unavailable or dataset too small; saved transition fallback metadata only.")
        return metadata

    x_tensor = torch.tensor(features, dtype=torch.long)
    y_tensor = torch.tensor(labels, dtype=torch.long)
    dataset = TensorDataset(x_tensor, y_tensor)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    model = LSTMNextProductModel(vocab_size=len(product_to_index))
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters())

    for _ in range(epochs):
        for batch_x, batch_y in loader:
            optimizer.zero_grad()
            output = model(batch_x)
            loss = criterion(output, batch_y)
            loss.backward()
            optimizer.step()

    model_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), model_path)

    metadata["model_type"] = "torch_lstm"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata
