"""
Rebuild the Neo4j knowledge graph from live catalog and behavioral events.
"""
from __future__ import annotations

import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from modules.ai.application.services import ProductCatalogLookupService
from modules.ai.infrastructure.domain_services import get_graph_service
from modules.ai.infrastructure.models import BehavioralEventModel
from modules.ai.infrastructure.repositories import DjangoBehavioralEventRepository


class Command(BaseCommand):
    help = "Rebuild Neo4j graph using catalog, behavioral events, and product relation seeds"

    def add_arguments(self, parser):
        parser.add_argument("--data-dir", default=str(settings.AI_DATA_DIR))
        parser.add_argument("--clear", action="store_true", help="Clear existing graph before rebuild")

    def handle(self, *args, **options):
        data_dir = Path(options["data_dir"])
        graph_service = get_graph_service()
        if options["clear"] and hasattr(graph_service, "clear_graph"):
            graph_service.clear_graph()
            self.stdout.write("Cleared existing graph")

        catalog = ProductCatalogLookupService().get_catalog_snapshot(page_size=200)
        for product in catalog:
            graph_service.upsert_product_node(product)
        self.stdout.write(f"Upserted {len(catalog)} product nodes")

        relations_csv = data_dir / "product_relations.csv"
        if relations_csv.exists():
            slug_to_product = {str(product.get("slug")): product for product in catalog if product.get("slug")}
            relation_count = 0
            with relations_csv.open("r", encoding="utf-8-sig", newline="") as file_obj:
                reader = csv.DictReader(file_obj)
                for row in reader:
                    source = slug_to_product.get(row.get("source_slug", ""))
                    target = slug_to_product.get(row.get("target_slug", ""))
                    if not source or not target:
                        continue
                    graph_service.link_similar_products(
                        source_product_id=str(source["id"]),
                        target_product_id=str(target["id"]),
                        weight=float(row.get("weight") or 1.0),
                        reason=row.get("reason") or "csv_dataset",
                    )
                    relation_count += 1
            self.stdout.write(f"Imported {relation_count} product relation edges")

        event_count = 0
        order_count = 0
        driver = getattr(graph_service, "driver", None)
        for event_model in BehavioralEventModel.objects.order_by("occurred_at").iterator():
            event = DjangoBehavioralEventRepository._model_to_entity(event_model)
            graph_service.sync_event_to_graph(event)
            event_count += 1

            order_id = (event.metadata or {}).get("order_id")
            if driver and order_id and event.user_id:
                with driver.session() as session:
                    session.run(
                        """
                        MERGE (o:Order {id: $order_id})
                        SET o.payment_status = $payment_status,
                            o.shipping_status = $shipping_status
                        MERGE (u:User {id: $user_id})
                        MERGE (u)-[:PLACED]->(o)
                        FOREACH (_ IN CASE WHEN $product_id IS NULL THEN [] ELSE [1] END |
                            MERGE (p:Product {id: $product_id})
                            MERGE (o)-[:CONTAINS]->(p)
                        )
                        """,
                        order_id=str(order_id),
                        user_id=str(event.user_id),
                        product_id=str(event.product_id) if event.product_id else None,
                        payment_status=(event.metadata or {}).get("payment_status"),
                        shipping_status=(event.metadata or {}).get("shipping_status"),
                    )
                order_count += 1

        self.stdout.write(self.style.SUCCESS(f"Rebuilt graph with {event_count} events and {order_count} order links"))
