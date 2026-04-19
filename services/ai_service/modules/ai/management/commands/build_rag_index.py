"""
Build the local RAG index from policies, FAQ, catalog, and CSV knowledge assets.
"""
from __future__ import annotations

import csv
import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from modules.ai.application.services import IngestKnowledgeDocumentUseCase, ProductCatalogLookupService
from modules.ai.infrastructure.models import KnowledgeChunkModel, KnowledgeDocumentModel


class Command(BaseCommand):
    help = "Build RAG knowledge documents and chunks from local files plus live catalog"

    def add_arguments(self, parser):
        parser.add_argument("--data-dir", default=str(settings.AI_DATA_DIR))
        parser.add_argument("--replace", action="store_true", help="Replace previously generated RAG documents")

    def handle(self, *args, **options):
        data_dir = Path(options["data_dir"])
        shared_data_dir = Path(os.getenv("TECHSHOP_SHARED_DATA_DIR", "/workspace-data"))
        if not shared_data_dir.exists():
            shared_data_dir = Path(settings.AI_DATA_DIR).parent.parent / "data"
        faq_dir = shared_data_dir / "faq"
        policy_dir = shared_data_dir / "policies"
        knowledge_csv = data_dir / "knowledge_documents.csv"
        ingest = IngestKnowledgeDocumentUseCase()

        if options["replace"]:
            generated_sources = ["rag_build", "rag_catalog", "csv_dataset"]
            docs = KnowledgeDocumentModel.objects.filter(source__in=generated_sources)
            KnowledgeChunkModel.objects.filter(document__in=docs).delete()
            docs.delete()
            self.stdout.write("Cleared previously generated RAG documents")

        total_documents = 0

        for doc_path in sorted(faq_dir.glob("*.md")):
            ingest.execute(
                title=doc_path.stem.replace("-", " ").title(),
                content=doc_path.read_text(encoding="utf-8"),
                document_type="faq",
                source="rag_build",
                slug=f"faq-{doc_path.stem}",
                metadata={"document_type": "faq", "path": str(doc_path)},
            )
            total_documents += 1

        for doc_path in sorted(policy_dir.glob("*.md")):
            document_type = "shipping_policy" if "shipping" in doc_path.name else "payment_policy" if "payment" in doc_path.name else "return_policy"
            ingest.execute(
                title=doc_path.stem.replace("-", " ").title(),
                content=doc_path.read_text(encoding="utf-8"),
                document_type=document_type,
                source="rag_build",
                slug=f"policy-{doc_path.stem}",
                metadata={"document_type": document_type, "path": str(doc_path)},
            )
            total_documents += 1

        if knowledge_csv.exists():
            with knowledge_csv.open("r", encoding="utf-8-sig", newline="") as file_obj:
                reader = csv.DictReader(file_obj)
                for row in reader:
                    slug = row.get("slug") or None
                    if slug:
                        KnowledgeChunkModel.objects.filter(document__slug=slug).delete()
                        KnowledgeDocumentModel.objects.filter(slug=slug).delete()
                    ingest.execute(
                        title=row["title"],
                        content=row["content"],
                        document_type=row["document_type"],
                        source="csv_dataset",
                        slug=slug,
                        metadata={"document_type": row["document_type"]},
                    )
                    total_documents += 1

        catalog = ProductCatalogLookupService().get_catalog_snapshot(page_size=200)
        grouped_lines = {}
        for product in catalog:
            category = str(product.get("category_name") or "uncategorized")
            grouped_lines.setdefault(category, []).append(
                f"- {product.get('name')} | brand={product.get('brand_name')} | price={product.get('base_price')} | tags={product.get('tags') or []}"
            )

        for category, lines in grouped_lines.items():
            slug = f"catalog-{category}".lower().replace(" ", "-")
            KnowledgeChunkModel.objects.filter(document__slug=slug).delete()
            KnowledgeDocumentModel.objects.filter(slug=slug).delete()
            ingest.execute(
                title=f"Catalog Guide - {category}",
                content=f"Catalog context for {category}\n\n" + "\n".join(lines),
                document_type="product_guide",
                source="rag_catalog",
                slug=slug,
                metadata={"document_type": "product_guide", "category_name": category},
            )
            total_documents += 1

        total_chunks = KnowledgeChunkModel.objects.count()
        self.stdout.write(self.style.SUCCESS(f"RAG index ready with {total_documents} documents and {total_chunks} chunks"))
