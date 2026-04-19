"""Sync published catalog products into AI knowledge storage."""

from django.core.management.base import BaseCommand

from modules.ai.application.services import SyncProductKnowledgeUseCase


class Command(BaseCommand):
    """Explicit command because product indexing is an operator-driven sync in this milestone."""

    help = "Sync published product catalog entries into AI knowledge documents"

    def add_arguments(self, parser):
        parser.add_argument("--page-size", type=int, default=100)

    def handle(self, *args, **options):
        result = SyncProductKnowledgeUseCase().execute(page_size=options["page_size"])
        self.stdout.write(self.style.SUCCESS(f"Indexed {result['products_indexed']} products"))
