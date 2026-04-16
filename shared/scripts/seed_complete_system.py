#!/usr/bin/env python3
"""
Master seed orchestration script for TechShop microservices.

This version is aligned with the current codebase and routes:
- Uses public/auth APIs where available.
- Uses Docker manage.py shell fallback for services that do not expose write APIs
  (notably product_service/order_service in this repository state).
- Keeps seeding idempotent (safe to run multiple times).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


REPO_ROOT = Path(__file__).resolve().parents[2]

SERVICE_URLS = {
    "user": os.getenv("USER_SERVICE_URL", "http://localhost:8001"),
    "product": os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8002"),
    "cart": os.getenv("CART_SERVICE_URL", "http://localhost:8003"),
    "order": os.getenv("ORDER_SERVICE_URL", "http://localhost:8004"),
    "payment": os.getenv("PAYMENT_SERVICE_URL", "http://localhost:8005"),
    "shipping": os.getenv("SHIPPING_SERVICE_URL", "http://localhost:8006"),
    "inventory": os.getenv("INVENTORY_SERVICE_URL", "http://localhost:8007"),
    "ai": os.getenv("AI_SERVICE_URL", "http://localhost:8008"),
}

INTERNAL_SERVICE_KEY = os.getenv("INTERNAL_SERVICE_KEY", "internal-secret-key")

DEMO_USERS = [
    {"email": "admin@example.com", "full_name": "Admin User", "phone_number": "+84912345670"},
    {"email": "staff@example.com", "full_name": "Staff User", "phone_number": "+84912345671"},
    {"email": "john@example.com", "full_name": "John Doe", "phone_number": "+84912345680"},
    {"email": "jane@example.com", "full_name": "Jane Doe", "phone_number": "+84912345681"},
]

DEMO_PASSWORD = "Demo@123456"

DEMO_CATEGORIES = [
    ("dien-thoai", "Dien thoai"),
    ("laptop", "Laptop"),
    ("tablet", "Tablet"),
    ("dong-ho-thong-minh", "Dong ho thong minh"),
    ("tai-nghe", "Tai nghe"),
    ("loa", "Loa"),
    ("phu-kien", "Phu kien"),
    ("man-hinh", "Man hinh"),
    ("linh-kien", "Linh kien"),
    ("gaming", "Gaming"),
]

DEMO_PRODUCTS = [
    ("iphone-15", "iPhone 15", "apple", 19990000, True),
    ("iphone-15-plus", "iPhone 15 Plus", "apple", 22990000, True),
    ("iphone-15-pro", "iPhone 15 Pro", "apple", 26990000, True),
    ("iphone-15-pro-max", "iPhone 15 Pro Max", "apple", 32990000, True),
    ("iphone-14", "iPhone 14", "apple", 16990000, False),
    ("iphone-se", "iPhone SE", "apple", 10990000, False),
    ("galaxy-s24", "Galaxy S24", "samsung", 18990000, False),
    ("galaxy-s24-plus", "Galaxy S24+", "samsung", 21990000, False),
    ("galaxy-s24-ultra", "Galaxy S24 Ultra", "samsung", 29990000, True),
    ("galaxy-a55", "Galaxy A55", "samsung", 9990000, False),
    ("galaxy-s23-fe", "Galaxy S23 FE", "samsung", 12990000, False),
    ("xiaomi-14", "Xiaomi 14", "xiaomi", 17990000, False),
    ("redmi-note-13-pro", "Redmi Note 13 Pro", "xiaomi", 7990000, False),
    ("redmi-note-13", "Redmi Note 13", "xiaomi", 6990000, False),
    ("redmi-13c", "Redmi 13C", "xiaomi", 3990000, False),
]

PRODUCT_MEDIA = {
    "iphone-15": [
        "https://www.apple.com/newsroom/images/2023/09/apple-debuts-iphone-15-and-iphone-15-plus/article/Apple-iPhone-15-lineup-design-230912_big.jpg.large.jpg",
        "https://www.apple.com/newsroom/images/2023/09/apple-debuts-iphone-15-and-iphone-15-plus/article/Apple-iPhone-15-lineup-hero-230912_inline.jpg.large.jpg",
        "https://www.apple.com/newsroom/images/2023/09/apple-debuts-iphone-15-and-iphone-15-plus/article/Apple-iPhone-15-48MP-01-230912_big.jpg.large.jpg",
        "https://www.apple.com/newsroom/images/2023/09/apple-debuts-iphone-15-and-iphone-15-plus/article/Apple-iPhone-15-Night-mode-230912_big.jpg.large.jpg",
    ],
    "iphone-15-plus": [
        "https://www.apple.com/newsroom/images/2023/09/apple-debuts-iphone-15-and-iphone-15-plus/article/Apple-iPhone-15-lineup-hero-230912_inline.jpg.large.jpg",
        "https://www.apple.com/newsroom/images/2023/09/apple-debuts-iphone-15-and-iphone-15-plus/article/Apple-iPhone-15-lineup-color-lineup-230912_big.jpg.large.jpg",
        "https://www.apple.com/newsroom/images/2023/09/apple-debuts-iphone-15-and-iphone-15-plus/article/Apple-iPhone-15-48MP-02-230912_big.jpg.large.jpg",
        "https://www.apple.com/newsroom/images/2023/09/apple-debuts-iphone-15-and-iphone-15-plus/article/Apple-iPhone-15-Portrait-mode-24MP-01-230912_big.jpg.large.jpg",
    ],
    "iphone-15-pro": [
        "https://www.apple.com/newsroom/images/2023/09/apple-unveils-iphone-15-pro-and-iphone-15-pro-max/article/Apple-iPhone-15-Pro-lineup-hero-230912_Full-Bleed-Image.jpg.large.jpg",
        "https://www.apple.com/newsroom/images/2023/09/apple-unveils-iphone-15-pro-and-iphone-15-pro-max/article/Apple-iPhone-15-Pro-lineup-color-lineup-230912_big.jpg.large.jpg",
        "https://www.apple.com/newsroom/images/2023/09/apple-unveils-iphone-15-pro-and-iphone-15-pro-max/article/Apple-iPhone-15-Pro-Photo-mode-Smart-HDR-230912_big.jpg.large.jpg",
        "https://www.apple.com/newsroom/images/2023/09/apple-unveils-iphone-15-pro-and-iphone-15-pro-max/article/Apple-iPhone-15-Pro-lineup-USB-C-connector-cable-230912_big.jpg.large.jpg",
    ],
    "iphone-15-pro-max": [
        "https://www.apple.com/newsroom/images/2023/09/apple-unveils-iphone-15-pro-and-iphone-15-pro-max/article/Apple-iPhone-15-Pro-lineup-hero-230912_Full-Bleed-Image.jpg.large.jpg",
        "https://www.apple.com/newsroom/images/2023/09/apple-unveils-iphone-15-pro-and-iphone-15-pro-max/article/Apple-iPhone-15-Pro-Max-48MP-camera-01-230912_big.jpg.large.jpg",
        "https://www.apple.com/newsroom/images/2023/09/apple-unveils-iphone-15-pro-and-iphone-15-pro-max/article/Apple-iPhone-15-Pro-Max-Telephoto-camera-230912_big.jpg.large.jpg",
        "https://www.apple.com/newsroom/images/2023/09/apple-unveils-iphone-15-pro-and-iphone-15-pro-max/article/Apple-iPhone-15-Pro-Max-Night-mode-Portrait-mode-230912_big.jpg.large.jpg",
    ],
    "iphone-14": [
        "https://images.unsplash.com/photo-1663767688549-1d7d1d8f3b8a?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1663767688549-1d7d1d8f3b8a?auto=format&fit=crop&w=900&q=80",
        "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?auto=format&fit=crop&w=900&q=80",
        "https://images.unsplash.com/photo-1512499617640-c2f999098c0b?auto=format&fit=crop&w=900&q=80",
    ],
    "iphone-se": [
        "https://images.unsplash.com/photo-1580910051074-3eb694886505?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1580910051074-3eb694886505?auto=format&fit=crop&w=900&q=80",
        "https://images.unsplash.com/photo-1565849904461-04a58ad377e0?auto=format&fit=crop&w=900&q=80",
        "https://images.unsplash.com/photo-1512499617640-c2f999098c0b?auto=format&fit=crop&w=900&q=80",
    ],
    "galaxy-s24": [
        "https://upload.wikimedia.org/wikipedia/commons/c/c7/Galaxy_S24_Ultra.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c7/Galaxy_S24_Ultra.jpg/960px-Galaxy_S24_Ultra.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c7/Galaxy_S24_Ultra.jpg/500px-Galaxy_S24_Ultra.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c7/Galaxy_S24_Ultra.jpg/360px-Galaxy_S24_Ultra.jpg",
    ],
    "galaxy-s24-plus": [
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/Samsung_Galaxy_S24_series.jpg",
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/Samsung_Galaxy_s24_series_2.jpg",
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/Samsung_Galaxy_S24.jpg",
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/Samsung_Galaxy_S24_01.jpg",
    ],
    "galaxy-s24-ultra": [
        "https://upload.wikimedia.org/wikipedia/commons/c/c7/Galaxy_S24_Ultra.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c7/Galaxy_S24_Ultra.jpg/960px-Galaxy_S24_Ultra.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c7/Galaxy_S24_Ultra.jpg/500px-Galaxy_S24_Ultra.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c7/Galaxy_S24_Ultra.jpg/360px-Galaxy_S24_Ultra.jpg",
    ],
    "galaxy-a55": [
        "https://upload.wikimedia.org/wikipedia/commons/b/b4/Galaxy_A55.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b4/Galaxy_A55.jpg/760px-Galaxy_A55.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b4/Galaxy_A55.jpg/500px-Galaxy_A55.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b4/Galaxy_A55.jpg/360px-Galaxy_A55.jpg",
    ],
    "galaxy-s23-fe": [
        "https://images.unsplash.com/photo-1595941069915-4ebc5197c14a?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1595941069915-4ebc5197c14a?auto=format&fit=crop&w=900&q=80",
        "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=900&q=80",
        "https://images.unsplash.com/photo-1622090186215-e9685a4f1b0e?auto=format&fit=crop&w=900&q=80",
    ],
    "xiaomi-14": [
        "https://upload.wikimedia.org/wikipedia/commons/7/71/%E5%B0%8F%E7%B1%B314_Pro%E5%92%8C%E5%B0%8F%E7%B1%B314%EF%BC%882024%E5%B9%B42%E6%9C%8820%E6%97%A5%EF%BC%89.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/7/71/%E5%B0%8F%E7%B1%B314_Pro%E5%92%8C%E5%B0%8F%E7%B1%B314%EF%BC%882024%E5%B9%B42%E6%9C%8820%E6%97%A5%EF%BC%89.jpg/1280px-%E5%B0%8F%E7%B1%B314_Pro%E5%92%8C%E5%B0%8F%E7%B1%B314%EF%BC%882024%E5%B9%B42%E6%9C%8820%E6%97%A5%EF%BC%89.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/7/71/%E5%B0%8F%E7%B1%B314_Pro%E5%92%8C%E5%B0%8F%E7%B1%B314%EF%BC%882024%E5%B9%B42%E6%9C%8820%E6%97%A5%EF%BC%89.jpg/960px-%E5%B0%8F%E7%B1%B314_Pro%E5%92%8C%E5%B0%8F%E7%B1%B314%EF%BC%882024%E5%B9%B42%E6%9C%8820%E6%97%A5%EF%BC%89.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/7/71/%E5%B0%8F%E7%B1%B314_Pro%E5%92%8C%E5%B0%8F%E7%B1%B314%EF%BC%882024%E5%B9%B42%E6%9C%8820%E6%97%A5%EF%BC%89.jpg/500px-%E5%B0%8F%E7%B1%B314_Pro%E5%92%8C%E5%B0%8F%E7%B1%B314%EF%BC%882024%E5%B9%B42%E6%9C%8820%E6%97%A5%EF%BC%89.jpg",
    ],
    "redmi-note-13-pro": [
        "https://images.unsplash.com/photo-1622620996948-5ba5c9c3fd8b?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1598327105666-5b89351aff97?auto=format&fit=crop&w=900&q=80",
        "https://images.unsplash.com/photo-1510557880182-3b9d8f0f2f5f?auto=format&fit=crop&w=900&q=80",
    ],
    "redmi-note-13": [
        "https://images.unsplash.com/photo-1622620996948-5ba5c9c3fd8b?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?auto=format&fit=crop&w=900&q=80",
        "https://images.unsplash.com/photo-1510557880182-3b9d8f0f2f5f?auto=format&fit=crop&w=900&q=80",
        "https://images.unsplash.com/photo-1512499617640-c2f999098c0b?auto=format&fit=crop&w=900&q=80",
    ],
    "redmi-13c": [
        "https://images.unsplash.com/photo-1622620996948-5ba5c9c3fd8b?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1598327105666-5b89351aff97?auto=format&fit=crop&w=900&q=80",
        "https://images.unsplash.com/photo-1510557880182-3b9d8f0f2f5f?auto=format&fit=crop&w=900&q=80",
        "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?auto=format&fit=crop&w=900&q=80",
    ],
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class SeedState:
    users: Dict[str, str] = field(default_factory=dict)
    products: List[Dict[str, Any]] = field(default_factory=list)
    carts: List[str] = field(default_factory=list)
    orders: List[str] = field(default_factory=list)
    inventory_items: List[str] = field(default_factory=list)
    ai_docs: List[str] = field(default_factory=list)
    ai_events_count: int = 0


class TechShopSeeder:
    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.state = SeedState()
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    # ------------------------
    # Helpers
    # ------------------------
    def _request(
        self,
        method: str,
        service: str,
        path: str,
        *,
        json_payload: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 10.0,
    ) -> requests.Response:
        url = f"{SERVICE_URLS[service]}{path}"
        merged_headers = dict(self.session.headers)
        if headers:
            merged_headers.update(headers)

        if self.verbose:
            logger.debug("%s %s payload=%s", method.upper(), url, json_payload)

        if self.dry_run:
            class DummyResponse:
                status_code = 200

                @staticmethod
                def json() -> Dict[str, Any]:
                    return {}

                text = ""

            return DummyResponse()  # type: ignore[return-value]

        return self.session.request(
            method=method.upper(),
            url=url,
            headers=merged_headers,
            json=json_payload,
            timeout=timeout,
        )

    def _run_cmd(self, args: List[str]) -> Tuple[bool, str]:
        cmd_text = " ".join(args)
        logger.debug("RUN: %s", cmd_text)
        if self.dry_run:
            return True, f"[DRY-RUN] {cmd_text}"

        proc = subprocess.run(
            args,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode == 0, out.strip()

    def _run_docker_manage(self, service: str, manage_args: List[str]) -> Tuple[bool, str]:
        return self._run_cmd(
            ["docker", "compose", "exec", "-T", service, "python", "manage.py", *manage_args]
        )

    def _run_docker_shell(self, service: str, python_code: str) -> Tuple[bool, str]:
        return self._run_docker_manage(service, ["shell", "-c", python_code])

    def _ensure_app_migrated(self, service: str, app_label: str) -> bool:
        """Ensure a Django app has migrations generated and applied."""
        show_ok, show_output = self._run_docker_manage(service, ["showmigrations", app_label])
        if not show_ok:
            logger.warning("  ✗ Could not inspect %s migrations: %s", app_label, show_output)
            return False

        if "no migrations" in show_output.lower():
            logger.info("  ! %s app has no migrations, generating with makemigrations...", app_label)
            mk_ok, mk_output = self._run_docker_manage(service, ["makemigrations", app_label])
            if not mk_ok:
                logger.warning("  ✗ makemigrations %s failed: %s", app_label, mk_output)
                return False

        migrate_ok, migrate_output = self._run_docker_manage(service, ["migrate", app_label])
        if not migrate_ok:
            logger.warning("  ✗ migrate %s failed: %s", app_label, migrate_output)
            return False
        return True

    @staticmethod
    def _extract_data(resp: requests.Response) -> Dict[str, Any]:
        try:
            payload = resp.json()
            if isinstance(payload, dict):
                return payload.get("data", {}) if "data" in payload else payload
        except Exception:
            pass
        return {}

    # ------------------------
    # Orchestration
    # ------------------------
    def seed_all(self) -> bool:
        logger.info("=" * 80)
        logger.info("STARTING COMPLETE SYSTEM SEED")
        logger.info("Dry Run: %s | Verbose: %s", self.dry_run, self.verbose)
        logger.info("=" * 80)

        ok = True
        ok = self.seed_users() and ok
        ok = self.seed_product_catalog() and ok
        ok = self.sync_ai_product_knowledge() and ok
        ok = self.seed_inventory() and ok
        ok = self.seed_carts() and ok
        ok = self.seed_orders_and_payments() and ok
        ok = self.seed_ai_knowledge_base() and ok
        ok = self.seed_ai_events() and ok
        self.print_summary()
        return ok

    # ------------------------
    # Phase 1: Users
    # ------------------------
    def seed_users(self) -> bool:
        logger.info("\n[PHASE 1] Seeding Users...")

        # Ensure demo users exist by calling register (idempotent-ish).
        for user in DEMO_USERS:
            payload = {
                "email": user["email"],
                "full_name": user["full_name"],
                "password": DEMO_PASSWORD,
                "confirm_password": DEMO_PASSWORD,
                "phone_number": user["phone_number"],
            }
            try:
                resp = self._request("post", "user", "/api/v1/auth/register/", json_payload=payload)
                if resp.status_code in (200, 201):
                    logger.info("  ✓ Registered: %s", user["email"])
                elif resp.status_code in (400, 409):
                    logger.info("  ✓ Exists: %s", user["email"])
                else:
                    logger.warning("  ✗ Register %s failed: %s", user["email"], resp.status_code)
            except Exception as exc:
                logger.warning("  ✗ Register %s error: %s", user["email"], exc)

        # Resolve user IDs via login.
        candidate_passwords = {
            "admin@example.com": [DEMO_PASSWORD, "admin123"],
            "staff@example.com": [DEMO_PASSWORD, "staff123"],
            "john@example.com": [DEMO_PASSWORD, "john123"],
            "jane@example.com": [DEMO_PASSWORD, "jane123"],
        }

        for user in DEMO_USERS:
            email = user["email"]
            resolved = False
            for pwd in candidate_passwords.get(email, [DEMO_PASSWORD]):
                try:
                    resp = self._request(
                        "post",
                        "user",
                        "/api/v1/auth/login/",
                        json_payload={"email": email, "password": pwd},
                    )
                    if resp.status_code == 200:
                        data = self._extract_data(resp)
                        user_id = (data.get("user") or {}).get("id")
                        if user_id:
                            self.state.users[email] = user_id
                            logger.info("  ✓ User ID resolved: %s -> %s", email, user_id)
                            resolved = True
                            break
                except Exception:
                    continue

            if not resolved:
                logger.warning("  ✗ Could not resolve user ID for %s", email)

        role_code = """
from modules.identity.infrastructure.models import User

targets = {
    "admin@example.com": ("admin", True),
    "staff@example.com": ("staff", True),
    "john@example.com": ("customer", False),
    "jane@example.com": ("customer", False),
}
for email, (role, is_staff) in targets.items():
    user = User.objects.filter(email=email).first()
    if not user:
        continue
    changed = False
    if user.role != role:
        user.role = role
        changed = True
    if user.is_staff != is_staff:
        user.is_staff = is_staff
        changed = True
    if not user.is_verified:
        user.is_verified = True
        changed = True
    if changed:
        user.save(update_fields=["role", "is_staff", "is_verified"])
        print("updated", email, role)
    else:
        print("ok", email, role)
""".strip()
        role_ok, role_output = self._run_docker_shell("user_service", role_code)
        if role_ok:
            logger.info("  ✓ User roles normalized for demo accounts")
        else:
            logger.warning("  ✗ Could not normalize user roles: %s", role_output)

        return len(self.state.users) >= 2

    # ------------------------
    # Phase 2-5: Product catalog
    # ------------------------
    def seed_product_catalog(self) -> bool:
        logger.info("\n[PHASE 2-5] Seeding Product Catalog...")

        # product_service currently lacks stable create APIs in this repo state,
        # so we seed using manage.py shell in container.
        code = f"""
from django.utils import timezone
from modules.catalog.infrastructure.models import CategoryModel, BrandModel, ProductTypeModel, ProductModel, ProductVariantModel

categories = {{}}
for idx, (slug, name) in enumerate({repr(DEMO_CATEGORIES)}, start=1):
    c, _ = CategoryModel.objects.get_or_create(
        slug=slug,
        defaults={{"name": name, "description": f"{{name}} category", "is_active": True, "sort_order": idx}},
    )
    categories[slug] = c
phone_type, _ = ProductTypeModel.objects.get_or_create(
    code="PHONE",
    defaults={{"name": "Phone", "description": "Smartphones", "is_active": True}},
)

brands = {{"apple": "Apple", "samsung": "Samsung", "xiaomi": "Xiaomi"}}
brand_objs = {{}}
for slug, name in brands.items():
    b, _ = BrandModel.objects.get_or_create(slug=slug, defaults={{"name": name, "is_active": True}})
    brand_objs[slug] = b

items = {repr(DEMO_PRODUCTS)}
media_map = {repr(PRODUCT_MEDIA)}
for idx, (slug, name, brand_slug, price, featured) in enumerate(items, start=1):
    p, _ = ProductModel.objects.get_or_create(
        slug=slug,
        defaults={{
            "name": name,
            "short_description": name,
            "description": f"{{name}} - demo product",
            "category": categories["dien-thoai"],
            "brand": brand_objs[brand_slug],
            "product_type": phone_type,
            "base_price": price,
            "currency": "VND",
            "status": "active",
            "is_active": True,
            "is_featured": featured,
            "thumbnail_url": media_map.get(slug, [f"https://images.unsplash.com/photo-1512499617640-c2f999098c0b?auto=format&fit=crop&w=1200&q=80"])[0],
            "published_at": timezone.now(),
        }},
    )
    changed = False
    if p.status != "active":
        p.status = "active"; changed = True
    if not p.is_active:
        p.is_active = True; changed = True
    if p.published_at is None:
        p.published_at = timezone.now(); changed = True
    if changed:
        p.save(update_fields=["status", "is_active", "published_at"])

    ProductVariantModel.objects.get_or_create(
        product=p,
        sku=f"{{slug.upper()}}-STD",
        defaults={{
            "name": "Standard",
            "is_default": True,
            "is_active": True,
            "price_override": price,
            "barcode": f"BAR{{100000 + idx}}",
        }},
    )

    for media_index, media_url in enumerate(media_map.get(slug, [])):
        p.media.get_or_create(
            media_url=media_url,
            defaults={{
                "alt_text": name + " image " + str(media_index + 1),
                "sort_order": media_index,
                "is_primary": media_index == 0,
            }},
        )

print("seeded_products", ProductModel.objects.filter(status="active", is_active=True, published_at__isnull=False).count())
""".strip()

        ok, output = self._run_docker_shell("product_service", code)
        if not ok:
            logger.error("  ✗ Product seed failed.\n%s", output)
            return False
        logger.info("  ✓ Product seed command completed")
        if self.verbose and output:
            logger.debug(output)

        # Refresh in-memory product list from public API.
        try:
            resp = self._request("get", "product", "/api/v1/catalog/products/?page_size=100")
            if resp.status_code == 200:
                payload = resp.json()
                self.state.products = payload.get("results", [])
                logger.info("  ✓ Public catalog count: %s", payload.get("count", 0))
            else:
                logger.warning("  ✗ Could not read product list: %s", resp.status_code)
        except Exception as exc:
            logger.warning("  ✗ Could not read product list: %s", exc)

        return len(self.state.products) > 0

    def sync_ai_product_knowledge(self) -> bool:
        logger.info("\n[PHASE 5B] Syncing AI Product Knowledge...")
        ok, output = self._run_docker_manage("ai_service", ["sync_product_knowledge", "--page-size", "100"])
        if not ok:
            logger.warning("  ✗ AI product knowledge sync failed: %s", output)
            return False
        logger.info("  ✓ AI product knowledge synced")
        if self.verbose and output:
            logger.debug(output)
        return True

    # ------------------------
    # Phase 6: Inventory
    # ------------------------
    def seed_inventory(self) -> bool:
        logger.info("\n[PHASE 6] Seeding Inventory...")
        self._ensure_app_migrated("inventory_service", "inventory")
        if not self.state.products:
            logger.warning("  ✗ No products available to seed inventory")
            return False

        admin_headers = {"X-Admin": "true"}
        created = 0

        for prod in self.state.products:
            product_id = prod.get("id")
            if not product_id:
                continue
            try:
                check = self._request(
                    "get",
                    "inventory",
                    f"/api/v1/admin/inventory/stock-items/?product_id={product_id}&limit=5",
                    headers=admin_headers,
                )
                exists = False
                if check.status_code == 200:
                    items = self._extract_data(check).get("items", [])
                    exists = len(items) > 0
                if exists:
                    continue

                create = self._request(
                    "post",
                    "inventory",
                    "/api/v1/admin/inventory/stock-items/",
                    headers=admin_headers,
                    json_payload={
                        "product_id": product_id,
                        "quantity": 40,
                        "warehouse_code": "MAIN",
                        "on_hand_quantity": 40,
                        "safety_stock": 5,
                    },
                )
                if create.status_code in (200, 201):
                    item_id = self._extract_data(create).get("id")
                    if item_id:
                        self.state.inventory_items.append(str(item_id))
                    created += 1
                else:
                    logger.debug("  Inventory create skipped for %s: %s", product_id, create.status_code)
            except Exception as exc:
                logger.debug("  Inventory error for %s: %s", product_id, exc)

        logger.info("  ✓ Inventory processed (new items: %s)", created)
        return True

    # ------------------------
    # Phase 7: Carts
    # ------------------------
    def seed_carts(self) -> bool:
        logger.info("\n[PHASE 7] Seeding Carts...")
        self._ensure_app_migrated("cart_service", "cart")
        john_id = self.state.users.get("john@example.com")
        jane_id = self.state.users.get("jane@example.com")
        if not john_id and not jane_id:
            logger.warning("  ✗ No customer users available for cart seed")
            return False
        if not self.state.products:
            logger.warning("  ✗ No products available for cart seed")
            return False

        def add_for_user(user_id: str, product_indexes: List[int]) -> None:
            headers = {"X-User-ID": user_id}
            for idx in product_indexes:
                if idx >= len(self.state.products):
                    continue
                p = self.state.products[idx]
                payload = {"product_id": p["id"], "quantity": 1}
                resp = self._request("post", "cart", "/api/v1/cart/items/", headers=headers, json_payload=payload)
                if resp.status_code not in (200, 201):
                    logger.debug("  add_item failed for user=%s product=%s: %s", user_id, p["id"], resp.status_code)

            current = self._request("get", "cart", "/api/v1/cart/current/", headers=headers)
            if current.status_code == 200:
                cart_data = self._extract_data(current)
                cart_id = cart_data.get("id")
                if cart_id:
                    self.state.carts.append(str(cart_id))

        if john_id:
            add_for_user(john_id, [0, 3])
            logger.info("  ✓ Cart seeded for john@example.com")
        if jane_id:
            add_for_user(jane_id, [1, 4])
            logger.info("  ✓ Cart seeded for jane@example.com")
        return True

    # ------------------------
    # Phase 8-10: Orders/Payments/Shipments
    # ------------------------
    def seed_orders_and_payments(self) -> bool:
        logger.info("\n[PHASE 8-10] Seeding Orders/Payments/Shipments...")
        john_id = self.state.users.get("john@example.com")
        jane_id = self.state.users.get("jane@example.com")
        if not (john_id and jane_id):
            logger.warning("  ✗ Missing John/Jane user IDs, skipping order seed")
            return False
        if len(self.state.products) < 2:
            logger.warning("  ✗ Not enough products, skipping order seed")
            return False

        order_seed_rows = [
            {
                "order_number": "ORD-SEED-001",
                "user_id": john_id,
                "status": "paid",
                "payment_status": "paid",
                "fulfillment_status": "preparing",
                "product": self.state.products[0],
                "qty": 1,
            },
            {
                "order_number": "ORD-SEED-002",
                "user_id": jane_id,
                "status": "shipping",
                "payment_status": "paid",
                "fulfillment_status": "shipped",
                "product": self.state.products[1],
                "qty": 1,
            },
        ]

        if not self._ensure_app_migrated("order_service", "order"):
            logger.warning("  ✗ Could not prepare order migrations, skipping order seed.")
            return True

        shell_payload = repr(order_seed_rows)
        code = f"""
import uuid
from decimal import Decimal
from django.utils import timezone
from modules.order.infrastructure.models import OrderModel, OrderItemModel, OrderStatusHistoryModel

rows = {shell_payload}
for row in rows:
    p = row["product"]
    qty = int(row["qty"])
    unit_price = Decimal(str(p.get("base_price", "0")))
    subtotal = unit_price * qty
    grand_total = subtotal + Decimal("30000")

    order, created = OrderModel.objects.get_or_create(
        order_number=row["order_number"],
        defaults={{
            "id": uuid.uuid4(),
            "user_id": row["user_id"],
            "cart_id": uuid.uuid4(),
            "status": row["status"],
            "payment_status": row["payment_status"],
            "fulfillment_status": row["fulfillment_status"],
            "currency": "VND",
            "subtotal_amount": subtotal,
            "shipping_fee_amount": Decimal("30000"),
            "discount_amount": Decimal("0"),
            "tax_amount": Decimal("0"),
            "grand_total_amount": grand_total,
            "total_quantity": qty,
            "item_count": 1,
            "customer_name_snapshot": "Demo Customer",
            "customer_email_snapshot": "demo@example.com",
            "customer_phone_snapshot": "0123456789",
            "receiver_name": "Demo Receiver",
            "receiver_phone": "0123456789",
            "shipping_line1": "123 Demo Street",
            "shipping_line2": "",
            "shipping_ward": "",
            "shipping_district": "District 1",
            "shipping_city": "Ho Chi Minh City",
            "shipping_country": "Vietnam",
            "shipping_postal_code": "",
            "notes": "Seeded by shared/scripts/seed_complete_system.py",
            "placed_at": timezone.now(),
            "paid_at": timezone.now() if row["payment_status"] == "paid" else None,
        }},
    )

    if created:
        OrderItemModel.objects.create(
            id=uuid.uuid4(),
            order=order,
            product_id=p["id"],
            variant_id=None,
            sku=f"{{p['slug'].upper()}}-STD",
            quantity=qty,
            unit_price=unit_price,
            line_total=subtotal,
            currency="VND",
            product_name_snapshot=p["name"],
            product_slug_snapshot=p["slug"],
            variant_name_snapshot="Standard",
            brand_name_snapshot=p.get("brand_name") or "",
            category_name_snapshot=p.get("category_name") or "",
            thumbnail_url_snapshot=p.get("thumbnail_url") or "",
            attributes_snapshot={{}},
        )
        OrderStatusHistoryModel.objects.create(
            id=uuid.uuid4(),
            order=order,
            from_status=None,
            to_status=row["status"],
            note="Seeded order",
            metadata={{"seed": True}},
        )
        print("created", order.order_number, order.id)
    else:
        print("exists", order.order_number, order.id)
""".strip()

        ok, output = self._run_docker_shell("order_service", code)
        if not ok:
            logger.warning("  ✗ Order seed skipped: %s", output)
            return True

        for line in output.splitlines():
            parts = line.strip().split()
            if len(parts) == 3 and parts[0] in {"created", "exists"}:
                self.state.orders.append(parts[2])
        logger.info("  ✓ Orders processed")
        return True

    # ------------------------
    # Phase 11: AI knowledge
    # ------------------------
    def seed_ai_knowledge_base(self) -> bool:
        logger.info("\n[PHASE 11] Seeding AI Knowledge Base...")
        docs = [
            {
                "title": "Shipping Policy",
                "document_type": "shipping_policy",
                "source": "seed_script",
                "content": "Free shipping for orders above 2,000,000 VND. Standard shipping 2-5 days.",
            },
            {
                "title": "Return Policy",
                "document_type": "return_policy",
                "source": "seed_script",
                "content": "Returns accepted within 30 days for unused items in original condition.",
            },
            {
                "title": "Payment Policy",
                "document_type": "payment_policy",
                "source": "seed_script",
                "content": "Accepted methods: card, bank transfer, and major e-wallets.",
            },
        ]

        created = 0
        for doc in docs:
            try:
                resp = self._request("post", "ai", "/api/v1/admin/ai/knowledge/", json_payload=doc)
                if resp.status_code in (200, 201):
                    doc_id = self._extract_data(resp).get("id")
                    if doc_id:
                        self.state.ai_docs.append(str(doc_id))
                    created += 1
                else:
                    logger.debug("  AI doc upsert skipped (%s): %s", doc["title"], resp.status_code)
            except Exception as exc:
                logger.debug("  AI doc error (%s): %s", doc["title"], exc)

        logger.info("  ✓ AI knowledge processed (new: %s)", created)
        return True

    # ------------------------
    # Phase 12: AI events
    # ------------------------
    def seed_ai_events(self) -> bool:
        logger.info("\n[PHASE 12] Seeding AI Behavioral Events...")
        if not self.state.products:
            logger.warning("  ✗ No products for AI events")
            return False

        john_id = self.state.users.get("john@example.com")
        jane_id = self.state.users.get("jane@example.com")
        if not (john_id or jane_id):
            logger.warning("  ✗ No users for AI events")
            return False

        events: List[Dict[str, Any]] = []
        for uid in [john_id, jane_id]:
            if not uid:
                continue
            for p in self.state.products[:4]:
                events.append(
                    {
                        "event_type": "product_view",
                        "user_id": uid,
                        "product_id": p["id"],
                        "brand_name": p.get("brand_name"),
                        "category_name": p.get("category_name"),
                        "price_amount": p.get("base_price"),
                        "source_service": "seed_script",
                        "metadata": {"seed": True},
                    }
                )

        try:
            resp = self._request(
                "post",
                "ai",
                "/api/v1/internal/ai/events/",
                json_payload={"events": events},
            )
            if resp.status_code in (200, 201):
                count = int(self._extract_data(resp).get("count", len(events)))
                self.state.ai_events_count = count
                logger.info("  ✓ AI events tracked: %s", count)
                return True
            logger.warning("  ✗ AI events failed: %s", resp.status_code)
            return False
        except Exception as exc:
            logger.warning("  ✗ AI events error: %s", exc)
            return False

    # ------------------------
    # Summary
    # ------------------------
    def print_summary(self) -> None:
        logger.info("\n" + "=" * 80)
        logger.info("SEEDING SUMMARY")
        logger.info("=" * 80)
        logger.info("Users resolved: %s", len(self.state.users))
        logger.info("Products available: %s", len(self.state.products))
        logger.info("Inventory items created: %s", len(self.state.inventory_items))
        logger.info("Carts prepared: %s", len(self.state.carts))
        logger.info("Orders prepared: %s", len(self.state.orders))
        logger.info("AI docs created: %s", len(self.state.ai_docs))
        logger.info("AI events tracked: %s", self.state.ai_events_count)
        if self.verbose:
            logger.debug("User IDs: %s", self.state.users)
        logger.info("=" * 80)
        logger.info("✓ SEEDING COMPLETE")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Master seed orchestration for TechShop microservices"
    )
    parser.add_argument("--clean", action="store_true", help="Reserved flag (not implemented)")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without applying")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--users-only", action="store_true", help="Seed only users")
    parser.add_argument("--products-only", action="store_true", help="Seed only product catalog")
    parser.add_argument("--orders-only", action="store_true", help="Seed only orders phase")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("Initializing TechShop Seeder...")
    logger.info("Services: %s", SERVICE_URLS)

    seeder = TechShopSeeder(dry_run=args.dry_run, verbose=args.verbose)

    if args.users_only:
        seeder.seed_users()
        seeder.print_summary()
        return
    if args.products_only:
        seeder.seed_product_catalog()
        seeder.seed_inventory()
        seeder.print_summary()
        return
    if args.orders_only:
        seeder.seed_users()
        seeder.seed_product_catalog()
        seeder.seed_orders_and_payments()
        seeder.print_summary()
        return

    success = seeder.seed_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
