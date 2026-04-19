"""
Load AI datasets from CSV files into PostgreSQL and Neo4j.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from modules.ai.application.services import IngestKnowledgeDocumentUseCase, ProductCatalogLookupService, RebuildUserPreferenceProfileUseCase, TrackBehavioralEventUseCase
from modules.ai.domain.value_objects import EventType
from modules.ai.infrastructure.domain_services import get_graph_service
from modules.ai.infrastructure.models import BehavioralEventModel, KnowledgeDocumentModel, UserPreferenceProfileModel
from modules.ai.infrastructure.sequence_models import train_lstm_model
from modules.ai.infrastructure.taxonomy import normalize_behavior_action


class Command(BaseCommand):
    """Import AI demo datasets from CSV."""

    help = "Load CSV datasets for behavior tracking, RAG knowledge, Neo4j graph, and optional LSTM training."

    def add_arguments(self, parser):
        parser.add_argument("--data-dir", default=str(settings.AI_DATA_DIR), help="Directory containing CSV datasets")
        parser.add_argument("--skip-knowledge", action="store_true", help="Skip loading knowledge_documents.csv")
        parser.add_argument("--skip-events", action="store_true", help="Skip loading data_100users.csv or user_behavior.csv")
        parser.add_argument("--skip-graph", action="store_true", help="Skip Neo4j sync/import")
        parser.add_argument("--train-lstm", action="store_true", help="Train LSTM model after loading events")
        parser.add_argument("--replace-demo", action="store_true", help="Delete previous csv_dataset records before import")
        parser.add_argument("--reset-graph", action="store_true", help="Clear Neo4j graph before import")

    def handle(self, *args, **options):
        data_dir = Path(options["data_dir"])
        if not data_dir.exists():
            raise CommandError(f"Data directory not found: {data_dir}")

        graph_service = None if options["skip_graph"] else get_graph_service()
        lookup_service = ProductCatalogLookupService()

        behavior_csv_path = self._resolve_behavior_csv_path(data_dir)

        if options["replace_demo"]:
            self._clear_demo_data(behavior_csv_path, graph_service, options["reset_graph"])

        live_catalog = self._load_live_catalog(lookup_service)
        csv_catalog = self._load_csv(data_dir / "product_catalog.csv")
        slug_mapping = self._build_slug_mapping(csv_catalog, live_catalog)

        if graph_service:
            self._sync_catalog_to_graph(slug_mapping, graph_service)
            self._load_product_relations(data_dir / "product_relations.csv", slug_mapping, graph_service)

        if not options["skip_knowledge"]:
            self._load_knowledge_documents(data_dir / "knowledge_documents.csv")

        imported_users = []
        if not options["skip_events"]:
            imported_users = self._load_behavior_events(behavior_csv_path, slug_mapping)
            self._rebuild_profiles(imported_users)

        if options["train_lstm"]:
            metadata = train_lstm_model(
                dataset_path=behavior_csv_path,
                model_path=Path(settings.LSTM_MODEL_PATH),
                metadata_path=Path(settings.LSTM_METADATA_PATH),
            )
            self.stdout.write(self.style.SUCCESS(f"LSTM artifact updated: {metadata.get('model_type')}"))

        self.stdout.write(self.style.SUCCESS("AI dataset import completed"))
        if imported_users:
            self.stdout.write("Imported demo users:")
            for user_id in imported_users:
                self.stdout.write(f"- {user_id}")

    def _clear_demo_data(self, behavior_csv_path: Path, graph_service, reset_graph: bool) -> None:
        user_ids = {
            row["user_id"]
            for row in self._load_csv(behavior_csv_path)
            if row.get("user_id")
        }
        BehavioralEventModel.objects.filter(source_service="csv_dataset").delete()
        UserPreferenceProfileModel.objects.filter(user_id__in=list(user_ids)).delete()
        KnowledgeDocumentModel.objects.filter(source="csv_dataset").delete()
        if graph_service and reset_graph and hasattr(graph_service, "clear_graph"):
            graph_service.clear_graph()
            self.stdout.write("Neo4j graph cleared before import")

    @staticmethod
    def _load_csv(csv_path: Path) -> List[Dict[str, str]]:
        if not csv_path.exists():
            raise CommandError(f"Missing dataset file: {csv_path}")
        with csv_path.open("r", encoding="utf-8-sig", newline="") as file_obj:
            return list(csv.DictReader(file_obj))

    @staticmethod
    def _resolve_behavior_csv_path(data_dir: Path) -> Path:
        canonical = data_dir / "data_100users.csv"
        legacy = data_dir / "user_behavior.csv"
        if canonical.exists():
            return canonical
        if legacy.exists():
            return legacy
        raise CommandError(f"Missing behavior dataset. Expected {canonical} or {legacy}")

    def _load_live_catalog(self, lookup_service: ProductCatalogLookupService) -> Dict[str, Dict[str, object]]:
        catalog_items = lookup_service._fetch_catalog_page(query="", page_size=200)
        if not catalog_items:
            raise CommandError("Could not load live catalog from product_service. Seed product_service first.")
        return {str(item.get("slug")): item for item in catalog_items if item.get("slug")}

    def _build_slug_mapping(
        self,
        csv_catalog: List[Dict[str, str]],
        live_catalog: Dict[str, Dict[str, object]],
    ) -> Dict[str, Dict[str, object]]:
        mapping: Dict[str, Dict[str, object]] = {}
        for row in csv_catalog:
            slug = row.get("slug")
            if not slug:
                continue
            live_product = live_catalog.get(slug)
            merged = {**row}
            if live_product:
                merged.update(
                    {
                        "id": live_product.get("id"),
                        "name": live_product.get("name"),
                        "slug": live_product.get("slug"),
                        "brand_name": live_product.get("brand_name"),
                        "category_name": live_product.get("category_name"),
                        "base_price": live_product.get("base_price"),
                        "short_description": live_product.get("short_description"),
                        "thumbnail_url": live_product.get("thumbnail_url"),
                        "is_featured": live_product.get("is_featured"),
                    }
                )
            mapping[slug] = merged
        return mapping

    def _sync_catalog_to_graph(self, slug_mapping: Dict[str, Dict[str, object]], graph_service) -> None:
        count = 0
        for product in slug_mapping.values():
            if product.get("id"):
                graph_service.upsert_product_node(product)
                count += 1
        self.stdout.write(f"Synced {count} products to Neo4j")

    def _load_product_relations(self, csv_path: Path, slug_mapping: Dict[str, Dict[str, object]], graph_service) -> None:
        count = 0
        for row in self._load_csv(csv_path):
            source = slug_mapping.get(row.get("source_slug", ""))
            target = slug_mapping.get(row.get("target_slug", ""))
            if not source or not target or not source.get("id") or not target.get("id"):
                continue
            graph_service.link_similar_products(
                source_product_id=str(source["id"]),
                target_product_id=str(target["id"]),
                weight=float(row.get("weight") or 1.0),
                reason=row.get("reason") or "csv_dataset",
            )
            count += 1
        self.stdout.write(f"Imported {count} product similarity edges into Neo4j")

    def _load_knowledge_documents(self, csv_path: Path) -> None:
        use_case = IngestKnowledgeDocumentUseCase()
        count = 0
        for row in self._load_csv(csv_path):
            metadata = json.loads(row.get("metadata") or "{}")
            slug = row.get("slug") or None
            if slug:
                KnowledgeDocumentModel.objects.filter(slug=slug).delete()
            else:
                KnowledgeDocumentModel.objects.filter(title=row["title"], source=row.get("source") or "csv_dataset").delete()
            use_case.execute(
                title=row["title"],
                content=row["content"],
                document_type=row["document_type"],
                source=row.get("source") or "csv_dataset",
                slug=slug,
                metadata=metadata,
            )
            count += 1
        self.stdout.write(f"Imported {count} knowledge documents")

    def _load_behavior_events(self, csv_path: Path, slug_mapping: Dict[str, Dict[str, object]]) -> List[str]:
        tracker = TrackBehavioralEventUseCase()
        imported_users: List[str] = []
        for row in self._load_csv(csv_path):
            product = slug_mapping.get(row.get("product_slug", "")) or {}
            product_id = row.get("product_id") or product.get("id")
            user_id = row.get("user_id")
            if user_id and user_id not in imported_users:
                imported_users.append(user_id)

            event_type = normalize_behavior_action(row.get("event_type") or row.get("action") or "")
            if event_type not in {item.value for item in EventType}:
                continue

            tracker.execute(
                event_type=event_type,
                user_id=UUID(user_id) if user_id else None,
                session_id=row.get("session_id") or None,
                product_id=UUID(str(product_id)) if product_id else None,
                brand_name=str(product.get("brand_name") or row.get("brand_name") or ""),
                category_name=str(product.get("category_name") or row.get("category_name") or row.get("category") or ""),
                price_amount=float(product.get("base_price") or row.get("price") or row.get("price_amount") or 0) if product.get("base_price") or row.get("price") or row.get("price_amount") else None,
                keyword=row.get("search_query") or row.get("keyword") or None,
                source_service="csv_dataset",
                occurred_at=_parse_datetime(row.get("timestamp")),
                metadata={
                    "dataset": "csv_dataset",
                    "product_slug": row.get("product_slug"),
                    "product_name": str(product.get("name")) if product.get("name") else None,
                    "order_id": row.get("order_id"),
                    "payment_status": row.get("payment_status"),
                    "shipping_status": row.get("shipping_status"),
                    "role": row.get("role"),
                    "age_group": row.get("age_group"),
                    "gender": row.get("gender"),
                    "cart_size": row.get("cart_size"),
                },
            )

        self.stdout.write(f"Imported {BehavioralEventModel.objects.filter(source_service='csv_dataset').count()} behavioral events")
        return imported_users

    def _rebuild_profiles(self, imported_users: List[str]) -> None:
        use_case = RebuildUserPreferenceProfileUseCase()
        for user_id in imported_users:
            use_case.execute(UUID(user_id))
        self.stdout.write(f"Rebuilt {len(imported_users)} user preference profiles")


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
