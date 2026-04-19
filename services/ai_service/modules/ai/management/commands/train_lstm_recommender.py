"""
Train the LSTM next-product recommender from CSV behavior data.
"""
from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from modules.ai.infrastructure.sequence_models import train_lstm_model


class Command(BaseCommand):
    """Train and persist sequence-model artifacts."""

    help = "Train the LSTM recommendation model from user_behavior.csv"

    def add_arguments(self, parser):
        default_dataset = Path(settings.AI_DATA_DIR) / "data_100users.csv"
        if not default_dataset.exists():
            default_dataset = Path(settings.AI_DATA_DIR) / "user_behavior.csv"
        parser.add_argument("--dataset", default=str(default_dataset))
        parser.add_argument("--sequence-length", type=int, default=5)
        parser.add_argument("--epochs", type=int, default=8)
        parser.add_argument("--batch-size", type=int, default=16)

    def handle(self, *args, **options):
        dataset_path = Path(options["dataset"])
        if not dataset_path.exists():
            raise CommandError(f"Dataset not found: {dataset_path}")

        metadata = train_lstm_model(
            dataset_path=dataset_path,
            model_path=Path(settings.LSTM_MODEL_PATH),
            metadata_path=Path(settings.LSTM_METADATA_PATH),
            sequence_length=options["sequence_length"],
            epochs=options["epochs"],
            batch_size=options["batch_size"],
        )

        self.stdout.write(self.style.SUCCESS("Sequence model training completed"))
        self.stdout.write(f"Model type: {metadata.get('model_type')}")
        self.stdout.write(f"Samples: {metadata.get('sample_count')}")
