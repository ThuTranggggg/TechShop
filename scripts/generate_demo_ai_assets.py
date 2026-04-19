"""
Generate demo AI datasets and knowledge assets for TechShop.

This script keeps the AI demo artifacts aligned with the live seeded catalog.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import random
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List


REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCT_SEED_FILE = REPO_ROOT / "services" / "product_service" / "modules" / "catalog" / "application" / "seed_data.py"
ROOT_DATA_DIR = REPO_ROOT / "data"
AI_DATA_DIR = REPO_ROOT / "services" / "ai_service" / "data"


def load_product_seed_module():
    spec = importlib.util.spec_from_file_location("techshop_seed_data", PRODUCT_SEED_FILE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


seed_module = load_product_seed_module()
PRODUCTS = seed_module.PRODUCT_SEED_DATA
stable_uuid = seed_module.stable_uuid

BASE_TIME = datetime(2026, 4, 1, 8, 0, tzinfo=timezone.utc)
AGE_GROUPS = ["18-24", "25-34", "35-44", "45-54"]
GENDERS = ["female", "male", "other"]
SEARCH_HINTS = {
    "electronics": ["laptop pin trau", "dien thoai chup anh dep", "tai nghe chong on", "man hinh gaming"],
    "fashion": ["ao khoac streetwear", "giay chay bo", "mu bucket", "quan jean form rong"],
    "cosmetics": ["son mau nude", "kem chong nang di bien", "kem nen cho da dau", "duong am makeup"],
    "home_appliances": ["may lanh tiet kiem dien", "tu lanh mini", "noi chien khong dau", "may loc khong khi"],
    "accessories": ["ban phim co khong day", "tui deo cheo", "op lung magsafe", "dong ho thong minh"],
    "books": ["sach tu duy phan tich", "sach thiet ke", "sach ky nang giao tiep"],
    "groceries": ["granola it duong", "tra hoa cuc", "ca phe hat rang"],
    "sports": ["tham yoga", "binh nuoc the thao", "vot cau long"],
    "baby_kids": ["ta bim size m", "do choi go cho be", "sua rua mat em be"],
    "furniture": ["ghe cong thai hoc", "ban lam viec compact", "ke sach go"],
    "office": ["so tay a5", "but gel mau den", "may in mini"],
    "toys": ["lego sang tao", "robot lap rap", "board game gia dinh"],
}
EVENT_TYPES = [
    "search",
    "view_category",
    "product_view",
    "product_click",
    "add_to_cart",
    "remove_from_cart",
    "add_to_wishlist",
    "checkout_started",
    "order_created",
    "payment_success",
    "order_cancel",
    "chat_query",
]

POLICY_FILES = {
    "shipping-policy.md": """# Shipping Policy

TechShop giao hang toan quoc bang nha van chuyen mock de demo.

- Don hang truoc 16:00 duoc tao shipment trong ngay.
- Trang thai demo: pending -> preparing -> in_transit -> delivered -> returned.
- Don gia tri cao duoc uu tien dong goi ky va co tracking.
- Staff co the cap nhat shipment status tu trang admin.
""",
    "payment-policy.md": """# Payment Policy

TechShop su dung mock payment de demo end-to-end checkout.

- Trang thai ho tro: unpaid, pending, paid, failed, refunded.
- Sau payment success he thong tao shipment mock tu dong.
- Neu xac nhan ton kho that bai, payment duoc danh dau refund/failed phu hop.
""",
    "return-policy.md": """# Return Policy

Khach hang co the yeu cau ho tro doi tra trong giai doan demo.

- San pham bi loi van chuyen co the bi danh dau returned.
- Staff co the cap nhat trang thai shipment ve returned de mo phong van hanh.
- Chatbot RAG se truy hoi chinh sach nay khi nguoi dung hoi ve doi tra.
""",
    "faq.md": """# FAQ

## TechShop co nhung nganh hang nao?
Electronics, fashion, cosmetics, home_appliances, accessories, books, groceries, sports va nhieu nhom mo rong khac.

## AI assistant co the lam gi?
Goi y san pham, search, add to cart, tao order, chat tra loi policy, va phan tich hanh vi.

## Recommendation duoc xay dung tu dau?
Tu behavioral events, LSTM sequence model, product co-occurrence, live catalog va Neo4j knowledge graph.
""",
}


def ensure_dirs() -> None:
    for directory in [
        ROOT_DATA_DIR,
        ROOT_DATA_DIR / "faq",
        ROOT_DATA_DIR / "policies",
        AI_DATA_DIR,
        AI_DATA_DIR / "models",
    ]:
        directory.mkdir(parents=True, exist_ok=True)


def stable_user_id(email: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"techshop-user:{email}"))


def build_catalog_rows() -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for product in PRODUCTS:
        description = f"{product['name']} thuoc nhom {product['category_slug']}, phu hop demo {product['item_type']} voi tags {', '.join(product.get('tags', []))}."
        rows.append(
            {
                "id": str(stable_uuid("product", product["slug"])),
                "slug": product["slug"],
                "name": product["name"],
                "category_name": product["category_slug"],
                "brand_name": product["brand_slug"],
                "base_price": str(product["price"]),
                "short_description": description,
                "thumbnail_url": f"https://images.unsplash.com/{product['slug']}?auto=format&fit=crop&w=800&q=80",
                "is_featured": str(bool(product.get("featured", False))).lower(),
                "item_type": product["item_type"],
                "rating": str(product.get("rating", 4.5)),
                "stock": str(product.get("stock", 10)),
                "tags": "|".join(product.get("tags", [])),
            }
        )
    return rows


def build_relation_rows(catalog_rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    by_category: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in catalog_rows:
        by_category[row["category_name"]].append(row)

    relations: List[Dict[str, str]] = []
    for category_rows in by_category.values():
        ordered = sorted(category_rows, key=lambda item: item["slug"])
        for idx, row in enumerate(ordered):
            for peer in ordered[idx + 1 : idx + 3]:
                relations.append(
                    {
                        "source_slug": row["slug"],
                        "target_slug": peer["slug"],
                        "weight": "0.82",
                        "reason": "same_category",
                    }
                )
    return relations


def build_knowledge_documents(catalog_rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    by_category: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in catalog_rows:
        by_category[row["category_name"]].append(row)

    rows: List[Dict[str, str]] = []
    for category_name, items in sorted(by_category.items()):
        top_items = sorted(items, key=lambda item: item["slug"])[:6]
        content_lines = [
            f"Danh muc {category_name} hien co {len(items)} san pham de demo.",
            "San pham noi bat:",
        ]
        for item in top_items:
            content_lines.append(
                f"- {item['name']} ({item['brand_name']}), gia {item['base_price']} VND, tags: {item['tags'] or 'n/a'}."
            )
        rows.append(
            {
                "slug": f"guide-{category_name}",
                "title": f"Product Guide - {category_name}",
                "document_type": "product_guide",
                "source": "csv_dataset",
                "content": "\n".join(content_lines),
                "metadata": json.dumps({"category_name": category_name, "document_type": "product_guide"}),
            }
        )

    rows.extend(
        [
            {
                "slug": "shipping-policy",
                "title": "Shipping Policy",
                "document_type": "shipping_policy",
                "source": "csv_dataset",
                "content": POLICY_FILES["shipping-policy.md"],
                "metadata": json.dumps({"document_type": "shipping_policy"}),
            },
            {
                "slug": "payment-policy",
                "title": "Payment Policy",
                "document_type": "payment_policy",
                "source": "csv_dataset",
                "content": POLICY_FILES["payment-policy.md"],
                "metadata": json.dumps({"document_type": "payment_policy"}),
            },
            {
                "slug": "return-policy",
                "title": "Return Policy",
                "document_type": "return_policy",
                "source": "csv_dataset",
                "content": POLICY_FILES["return-policy.md"],
                "metadata": json.dumps({"document_type": "return_policy"}),
            },
            {
                "slug": "faq-techshop",
                "title": "TechShop FAQ",
                "document_type": "faq",
                "source": "csv_dataset",
                "content": POLICY_FILES["faq.md"],
                "metadata": json.dumps({"document_type": "faq"}),
            },
        ]
    )
    return rows


def choose_products_for_category(catalog_rows: List[Dict[str, str]], category: str, count: int, rng: random.Random) -> List[Dict[str, str]]:
    matches = [row for row in catalog_rows if row["category_name"] == category]
    return rng.sample(matches, k=min(count, len(matches)))


def append_event(
    rows: List[Dict[str, str]],
    *,
    user_id: str,
    role: str,
    age_group: str,
    gender: str,
    timestamp: datetime,
    event_type: str,
    product: Dict[str, str] | None,
    category: str,
    search_query: str = "",
    cart_size: int = 0,
    order_id: str = "",
    payment_status: str = "unpaid",
    shipping_status: str = "pending",
    session_id: str,
) -> None:
    rows.append(
        {
            "user_id": user_id,
            "role": role,
            "age_group": age_group,
            "gender": gender,
            "timestamp": timestamp.isoformat(),
            "event_type": event_type,
            "product_id": product["id"] if product else "",
            "product_slug": product["slug"] if product else "",
            "product_name": product["name"] if product else "",
            "brand_name": product["brand_name"] if product else "",
            "category": category,
            "search_query": search_query,
            "cart_size": str(cart_size),
            "price": product["base_price"] if product else "",
            "order_id": order_id,
            "payment_status": payment_status,
            "shipping_status": shipping_status,
            "session_id": session_id,
        }
    )


def generate_behavior_rows(catalog_rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    category_cycle = sorted({row["category_name"] for row in catalog_rows})
    rows: List[Dict[str, str]] = []

    for index in range(1, 101):
        email = f"user{index:03d}@example.com"
        user_id = stable_user_id(email)
        role = "admin" if index <= 5 else "staff" if index <= 15 else "customer"
        age_group = AGE_GROUPS[(index - 1) % len(AGE_GROUPS)]
        gender = GENDERS[(index - 1) % len(GENDERS)]
        preferred_category = category_cycle[(index - 1) % len(category_cycle)]
        secondary_category = category_cycle[(index + 3) % len(category_cycle)]
        rng = random.Random(20260417 + index)
        current_time = BASE_TIME + timedelta(hours=index)

        for session_idx in range(1, 4):
            session_id = f"sess-{index:03d}-{session_idx:02d}"
            journey = ["browse_then_buy", "browse_only", "chat_then_buy", "wishlist_drop", "cancel_order", "repeat_buy"][
                (index + session_idx) % 6
            ]
            focus_category = preferred_category if session_idx % 2 else secondary_category
            featured_products = choose_products_for_category(catalog_rows, focus_category, 3, rng)
            search_query = rng.choice(SEARCH_HINTS.get(focus_category, ["techshop demo"]))
            cart_size = 0
            order_id = f"ORD-{index:03d}-{session_idx:02d}"

            append_event(
                rows,
                user_id=user_id,
                role=role,
                age_group=age_group,
                gender=gender,
                timestamp=current_time,
                event_type="search",
                product=None,
                category=focus_category,
                search_query=search_query,
                cart_size=cart_size,
                order_id="",
                payment_status="unpaid",
                shipping_status="pending",
                session_id=session_id,
            )
            current_time += timedelta(minutes=5)

            append_event(
                rows,
                user_id=user_id,
                role=role,
                age_group=age_group,
                gender=gender,
                timestamp=current_time,
                event_type="view_category",
                product=None,
                category=focus_category,
                search_query=search_query,
                cart_size=cart_size,
                order_id="",
                payment_status="unpaid",
                shipping_status="pending",
                session_id=session_id,
            )
            current_time += timedelta(minutes=4)

            for product in featured_products[:2]:
                append_event(
                    rows,
                    user_id=user_id,
                    role=role,
                    age_group=age_group,
                    gender=gender,
                    timestamp=current_time,
                    event_type="product_view",
                    product=product,
                    category=focus_category,
                    search_query=search_query,
                    cart_size=cart_size,
                    order_id="",
                    payment_status="unpaid",
                    shipping_status="pending",
                    session_id=session_id,
                )
                current_time += timedelta(minutes=3)
                append_event(
                    rows,
                    user_id=user_id,
                    role=role,
                    age_group=age_group,
                    gender=gender,
                    timestamp=current_time,
                    event_type="product_click",
                    product=product,
                    category=focus_category,
                    search_query=search_query,
                    cart_size=cart_size,
                    order_id="",
                    payment_status="unpaid",
                    shipping_status="pending",
                    session_id=session_id,
                )
                current_time += timedelta(minutes=3)

            lead_product = featured_products[0]

            if journey == "browse_only":
                continue

            if journey in {"chat_then_buy", "repeat_buy"}:
                append_event(
                    rows,
                    user_id=user_id,
                    role=role,
                    age_group=age_group,
                    gender=gender,
                    timestamp=current_time,
                    event_type="chat_query",
                    product=lead_product,
                    category=focus_category,
                    search_query=f"goi y {search_query}",
                    cart_size=cart_size,
                    order_id="",
                    payment_status="unpaid",
                    shipping_status="pending",
                    session_id=session_id,
                )
                current_time += timedelta(minutes=2)

            if journey in {"wishlist_drop", "chat_then_buy"}:
                append_event(
                    rows,
                    user_id=user_id,
                    role=role,
                    age_group=age_group,
                    gender=gender,
                    timestamp=current_time,
                    event_type="add_to_wishlist",
                    product=lead_product,
                    category=focus_category,
                    search_query="",
                    cart_size=cart_size,
                    order_id="",
                    payment_status="unpaid",
                    shipping_status="pending",
                    session_id=session_id,
                )
                current_time += timedelta(minutes=2)

            cart_size += 1
            append_event(
                rows,
                user_id=user_id,
                role=role,
                age_group=age_group,
                gender=gender,
                timestamp=current_time,
                event_type="add_to_cart",
                product=lead_product,
                category=focus_category,
                search_query="",
                cart_size=cart_size,
                order_id="",
                payment_status="unpaid",
                shipping_status="pending",
                session_id=session_id,
            )
            current_time += timedelta(minutes=3)

            if journey == "wishlist_drop":
                cart_size = 0
                append_event(
                    rows,
                    user_id=user_id,
                    role=role,
                    age_group=age_group,
                    gender=gender,
                    timestamp=current_time,
                    event_type="remove_from_cart",
                    product=lead_product,
                    category=focus_category,
                    search_query="",
                    cart_size=cart_size,
                    order_id="",
                    payment_status="unpaid",
                    shipping_status="pending",
                    session_id=session_id,
                )
                current_time += timedelta(minutes=2)
                continue

            append_event(
                rows,
                user_id=user_id,
                role=role,
                age_group=age_group,
                gender=gender,
                timestamp=current_time,
                event_type="checkout_started",
                product=lead_product,
                category=focus_category,
                search_query="",
                cart_size=cart_size,
                order_id=order_id,
                payment_status="pending",
                shipping_status="pending",
                session_id=session_id,
            )
            current_time += timedelta(minutes=4)

            append_event(
                rows,
                user_id=user_id,
                role=role,
                age_group=age_group,
                gender=gender,
                timestamp=current_time,
                event_type="order_created",
                product=lead_product,
                category=focus_category,
                search_query="",
                cart_size=cart_size,
                order_id=order_id,
                payment_status="pending",
                shipping_status="pending",
                session_id=session_id,
            )
            current_time += timedelta(minutes=4)

            if journey == "cancel_order":
                append_event(
                    rows,
                    user_id=user_id,
                    role=role,
                    age_group=age_group,
                    gender=gender,
                    timestamp=current_time,
                    event_type="order_cancel",
                    product=lead_product,
                    category=focus_category,
                    search_query="",
                    cart_size=0,
                    order_id=order_id,
                    payment_status="failed",
                    shipping_status="returned",
                    session_id=session_id,
                )
                current_time += timedelta(minutes=2)
                continue

            shipping_status = "delivered" if (index + session_idx) % 4 == 0 else "in_transit" if (index + session_idx) % 3 == 0 else "preparing"
            append_event(
                rows,
                user_id=user_id,
                role=role,
                age_group=age_group,
                gender=gender,
                timestamp=current_time,
                event_type="payment_success",
                product=lead_product,
                category=focus_category,
                search_query="",
                cart_size=cart_size,
                order_id=order_id,
                payment_status="paid",
                shipping_status=shipping_status,
                session_id=session_id,
            )
            current_time += timedelta(minutes=6)

            if journey == "repeat_buy":
                extra_product = featured_products[-1]
                cart_size = 1
                extra_order_id = f"{order_id}-R"
                append_event(
                    rows,
                    user_id=user_id,
                    role=role,
                    age_group=age_group,
                    gender=gender,
                    timestamp=current_time,
                    event_type="product_view",
                    product=extra_product,
                    category=focus_category,
                    search_query="mua lai",
                    cart_size=0,
                    order_id="",
                    payment_status="unpaid",
                    shipping_status="pending",
                    session_id=session_id,
                )
                current_time += timedelta(minutes=2)
                append_event(
                    rows,
                    user_id=user_id,
                    role=role,
                    age_group=age_group,
                    gender=gender,
                    timestamp=current_time,
                    event_type="add_to_cart",
                    product=extra_product,
                    category=focus_category,
                    search_query="",
                    cart_size=cart_size,
                    order_id="",
                    payment_status="unpaid",
                    shipping_status="pending",
                    session_id=session_id,
                )
                current_time += timedelta(minutes=2)
                append_event(
                    rows,
                    user_id=user_id,
                    role=role,
                    age_group=age_group,
                    gender=gender,
                    timestamp=current_time,
                    event_type="order_created",
                    product=extra_product,
                    category=focus_category,
                    search_query="",
                    cart_size=cart_size,
                    order_id=extra_order_id,
                    payment_status="pending",
                    shipping_status="pending",
                    session_id=session_id,
                )
                current_time += timedelta(minutes=2)
                append_event(
                    rows,
                    user_id=user_id,
                    role=role,
                    age_group=age_group,
                    gender=gender,
                    timestamp=current_time,
                    event_type="payment_success",
                    product=extra_product,
                    category=focus_category,
                    search_query="",
                    cart_size=cart_size,
                    order_id=extra_order_id,
                    payment_status="paid",
                    shipping_status="delivered",
                    session_id=session_id,
                )
                current_time += timedelta(minutes=4)

    return rows


def build_user_behavior_rows(behavior_rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for row in behavior_rows:
        rows.append(
            {
                "user_id": row["user_id"],
                "session_id": row["session_id"],
                "timestamp": row["timestamp"],
                "action": row["event_type"],
                "product_id": row["product_id"],
                "product_slug": row["product_slug"],
                "product_name": row["product_name"],
                "brand_name": row["brand_name"],
                "category_name": row["category"],
                "price_amount": row["price"],
                "keyword": row["search_query"],
                "order_id": row["order_id"],
                "payment_status": row["payment_status"],
                "shipping_status": row["shipping_status"],
            }
        )
    return rows


def write_csv(path: Path, rows: List[Dict[str, str]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_text_assets() -> None:
    for filename, content in POLICY_FILES.items():
        target_dir = ROOT_DATA_DIR / ("policies" if "policy" in filename else "faq")
        (target_dir / filename).write_text(content, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    catalog_rows = build_catalog_rows()
    relation_rows = build_relation_rows(catalog_rows)
    knowledge_rows = build_knowledge_documents(catalog_rows)
    behavior_rows = generate_behavior_rows(catalog_rows)
    user_behavior_rows = build_user_behavior_rows(behavior_rows)

    write_csv(REPO_ROOT / "data_100users.csv", behavior_rows)
    write_csv(ROOT_DATA_DIR / "data_100users.csv", behavior_rows)
    write_csv(AI_DATA_DIR / "data_100users.csv", behavior_rows)
    write_csv(AI_DATA_DIR / "user_behavior.csv", user_behavior_rows)
    write_csv(AI_DATA_DIR / "product_catalog.csv", catalog_rows)
    write_csv(AI_DATA_DIR / "product_relations.csv", relation_rows)
    write_csv(AI_DATA_DIR / "knowledge_documents.csv", knowledge_rows)
    write_text_assets()

    print(f"Generated {len(catalog_rows)} catalog rows")
    print(f"Generated {len(behavior_rows)} behavioral events for 100 users")
    print(f"Generated {len(relation_rows)} product relations")
    print(f"Generated {len(knowledge_rows)} knowledge documents")


if __name__ == "__main__":
    main()
