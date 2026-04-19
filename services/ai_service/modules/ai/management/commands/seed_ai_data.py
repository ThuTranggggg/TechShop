"""
Management command to seed AI service data.
Demonstrates behavioral tracking, preferences, and recommendations.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from uuid import uuid4
from datetime import datetime, timedelta
import random

from modules.ai.application.services import (
    TrackBehavioralEventUseCase,
    IngestKnowledgeDocumentUseCase,
)
from modules.ai.infrastructure.models import (
    KnowledgeDocumentModel,
)


class Command(BaseCommand):
    """Seed AI service data."""

    help = "Seed AI service with demo data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--users",
            type=int,
            default=3,
            help="Number of users to create events for"
        )
        parser.add_argument(
            "--events-per-user",
            type=int,
            default=50,
            help="Number of events per user"
        )
        parser.add_argument(
            "--skip-knowledge",
            action="store_true",
            help="Skip knowledge document seeding"
        )

    def handle(self, *args, **options):
        self.stdout.write("Seeding AI service data...")

        num_users = options["users"]
        events_per_user = options["events_per_user"]
        skip_knowledge = options["skip_knowledge"]

        # Seed knowledge documents
        if not skip_knowledge:
            self.seed_knowledge_documents()

        # Seed behavioral events
        self.seed_behavioral_events(num_users, events_per_user)

        self.stdout.write(self.style.SUCCESS("Seeding complete!"))

    def seed_knowledge_documents(self):
        """Seed knowledge documents for RAG."""
        self.stdout.write("Seeding knowledge documents...")

        documents = [
            {
                "title": "Return Policy",
                "document_type": "return_policy",
                "content": """
Our return policy is simple and customer-friendly:

1. Returns are accepted within 30 days of purchase with original receipt
2. Items must be unused and in original packaging
3. Electronics must be in factory sealed condition
4. Clothing items cannot be returned if tags are removed
5. Customized items cannot be returned

TO INITIATE A RETURN:
- Visit your account and select the order
- Select the item to return
- Choose a reason
- Print the return label or arrange pickup
- Ship the item back to us

REFUND PROCESS:
- We inspect items upon receipt
- Approved refunds are processed within 5-7 business days
- Refunds are issued to the original payment method
- Return shipping is free for defective items

For questions, contact our support team at support@techshop.com
                """,
            },
            {
                "title": "Payment Policy",
                "document_type": "payment_policy",
                "content": """
ACCEPTED PAYMENT METHODS:
- Credit/Debit Cards (Visa, Mastercard, American Express)
- Online Banking (Vietcombank, MB Bank, ACB, Vietinbank)
- Digital Wallets (Momo, Zalopay)
- Buy Now Pay Later (Klarna, Affirm)
- Bank Transfer

PAYMENT SECURITY:
- All payments are encrypted with SSL
- We use PCI DSS Level 1 compliance
- Your card information is not stored on our servers
- 3D Secure verification required for all transactions

PAYMENT FAILED:
If your payment fails, please:
1. Verify your card details
2. Check your card balance
3. Contact your bank
4. Try a different payment method

REFUND TIMELINE:
- Credit card refunds: 5-10 business days
- Bank transfer refunds: 2-5 business days
- Digital wallet refunds: instant
                """,
            },
            {
                "title": "Shipping Policy",
                "document_type": "shipping_policy",
                "content": """
SHIPPING OPTIONS:

Express Shipping:
- Delivery within 24 hours in Ho Chi Minh City
- Delivery within 2 days in major cities
- Cost: 50,000 VND
- Track in real-time

Standard Shipping:
- Delivery within 3-7 days nationwide
- Cost: 30,000 VND
- Includes tracking

Free Shipping:
- Orders over 1,000,000 VND
- Delivery within 7-10 business days
- Nationwide coverage

International Shipping:
- Available to 50+ countries
- Cost: from 200,000 VND
- Delivery: 10-30 business days

TRACKING:
- Track orders in your account
- Receive SMS/email updates
- Real-time courier information available
                """,
            },
        ]

        for doc_data in documents:
            if not KnowledgeDocumentModel.objects.filter(title=doc_data["title"]).exists():
                use_case = IngestKnowledgeDocumentUseCase()
                use_case.execute(**doc_data)
                self.stdout.write(f"Created: {doc_data['title']}")

    def seed_behavioral_events(self, num_users, events_per_user):
        """Seed behavioral events for demonstration."""
        self.stdout.write(f"Seeding {num_users} users with {events_per_user} events each...")

        # Demo data
        brands = ["Samsung", "Apple", "Nokia", "Xiaomi", "Oppo", "Vivo", "Realme", "Sony"]
        categories = ["Smartphone", "Laptop", "Tablet", "Camera", "Smartwatch", "Headphones"]
        price_amounts = [5_000_000, 8_000_000, 12_000_000, 15_000_000, 20_000_000, 25_000_000]

        event_types_dist = [
            ("search", 0.2),
            ("product_view", 0.3),
            ("product_click", 0.25),
            ("add_to_cart", 0.15),
            ("checkout_started", 0.05),
            ("order_created", 0.03),
            ("payment_success", 0.02),
        ]

        use_case = TrackBehavioralEventUseCase()

        for user_num in range(num_users):
            user_id = uuid4()
            self.stdout.write(f"Creating events for user: {user_id}")

            # Create scenario: user prefers Samsung under 10M
            samsung_score = 0
            nokia_score = 0

            for event_num in range(events_per_user):
                # Randomize event type
                rand = random.random()
                cumul = 0
                event_type = "search"
                for etype, prob in event_types_dist:
                    cumul += prob
                    if rand <= cumul:
                        event_type = etype
                        break

                # Favor Samsung under 10M for this demo user
                if random.random() < 0.6:  # 60% chance to interact with Samsung
                    brand = "Samsung"
                    price = random.choice([5_000_000, 8_000_000, 9_000_000])
                    samsung_score += 1
                elif random.random() < 0.3:  # 30% chance for Nike  (just another example)
                    brand = "Nokia"
                    price = random.choice(price_amounts)
                    nokia_score += 1
                else:
                    brand = random.choice(brands)
                    price = random.choice(price_amounts)

                # Create event
                timestamp = timezone.now() - timedelta(days=random.randint(0, 30))

                use_case.execute(
                    event_type=event_type,
                    user_id=user_id,
                    session_id=f"session_{user_num}_{event_num % 5}",
                    product_id=uuid4(),
                    brand_name=brand,
                    category_name=random.choice(categories),
                    price_amount=float(price),
                    keyword=f"search {brand.lower()}" if event_type == "search" else None,
                    source_service="demo",
                    metadata={"demo": True, "scenario": "samsung_preference"},
                    occurred_at=timestamp,
                )

            self.stdout.write(f"  Created {events_per_user} events")
            self.stdout.write(f"  Samsung interactions: {samsung_score}, Nokia: {nokia_score}")

        self.stdout.write(self.style.SUCCESS(f"Seeded {num_users} users successfully"))
