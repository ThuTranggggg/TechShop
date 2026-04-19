"""
Shared product taxonomy and text helpers for AI service.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Set


PRODUCT_GROUP_ALIASES: Dict[str, List[str]] = {
    "dien tu": ["dien tu", "cong nghe", "tech", "do cong nghe", "electrics", "electronics"],
    "thoi trang": ["thoi trang", "quan ao", "fashion", "mac dep"],
    "my pham": ["my pham", "lam dep", "cosmetics", "beauty"],
    "nha cua doi song": ["nha cua doi song", "gia dung", "home", "doi song", "do gia dung"],
    "me va be": ["me va be", "baby", "kids care", "tre em so sinh"],
    "the thao da ngoai": ["the thao da ngoai", "the thao", "outdoor", "camping", "fitness"],
    "sach van phong pham": ["sach van phong pham", "sach", "van phong pham", "stationery", "books"],
    "thuc pham do uong": ["thuc pham do uong", "do an vat", "thuc pham", "do uong", "food", "drink"],
    "suc khoe ca nhan": ["suc khoe ca nhan", "suc khoe", "wellness", "personal care"],
    "do choi giai tri": ["do choi giai tri", "do choi", "boardgame", "toy", "giai tri"],
    "cham soc thu cung": ["cham soc thu cung", "thu cung", "pet", "cho meo"],
}

CATEGORY_ALIASES: Dict[str, List[str]] = {
    "dien thoai va may tinh bang": ["dien thoai", "smartphone", "tablet", "may tinh bang", "mobile"],
    "phu kien cong nghe": ["phu kien cong nghe", "tai nghe", "pin du phong", "sac", "accessory"],
    "thoi trang nam": ["thoi trang nam", "ao nam", "quan nam", "nam gioi"],
    "thoi trang nu": ["thoi trang nu", "dam", "ao nu", "women fashion", "nu gioi"],
    "cham soc da": ["cham soc da", "serum", "kem duong", "skincare"],
    "trang diem": ["trang diem", "son", "cushion", "makeup"],
    "do bep": ["do bep", "noi chien", "chao", "kitchen"],
    "trang tri nha cua": ["trang tri nha cua", "den ngu", "ke sach", "decor"],
    "do so sinh": ["do so sinh", "quan ao so sinh", "newborn"],
    "sua va bim": ["sua va bim", "bim", "ta dan", "sua cong thuc"],
    "do tap luyen": ["do tap luyen", "yoga", "ta tay", "fitness gear"],
    "da ngoai cam trai": ["da ngoai cam trai", "leu", "cam trai", "camping"],
    "sach ky nang": ["sach ky nang", "sach tai chinh", "self help"],
    "van phong pham": ["van phong pham", "so tay", "but gel", "stationery"],
    "do an vat": ["do an vat", "snack", "hat dinh duong"],
    "do uong pha san": ["do uong pha san", "ca phe", "tra", "ready drink"],
    "vitamin bo sung": ["vitamin bo sung", "vitamin", "collagen", "supplement"],
    "cham soc ca nhan": ["cham soc ca nhan", "ban chai dien", "may do huyet ap", "personal care"],
    "do choi giao duc": ["do choi giao duc", "xep hinh", "hoc chu cai", "educational toy"],
    "boardgame mo hinh": ["boardgame mo hinh", "boardgame", "mo hinh", "lap rap"],
    "thuc an thu cung": ["thuc an thu cung", "pate", "hat cho meo", "pet food"],
    "phu kien thu cung": ["phu kien thu cung", "day dan", "cat ve sinh", "pet accessory"],
}

PRICE_FILTER_PATTERNS: Dict[str, List[str]] = {
    "under_1m": ["duoi 1 trieu", "re", "gia re", "under 1m"],
    "under_3m": ["duoi 3 trieu", "under 3m"],
    "under_5m": ["duoi 5 trieu", "under 5m"],
    "under_10m": ["duoi 10 trieu", "under 10m"],
    "above_20m": ["tren 20 trieu", "hon 20 trieu", "above 20m"],
}


def normalize_text(text: str) -> str:
    """Normalize Vietnamese text to ASCII-like tokens."""
    normalized = unicodedata.normalize("NFD", str(text).lower())
    without_marks = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    collapsed = without_marks.replace("đ", "d")
    return re.sub(r"\s+", " ", collapsed).strip()


def tokenize(text: str) -> List[str]:
    """Tokenize normalized text into useful terms."""
    normalized = normalize_text(text)
    return [token for token in re.split(r"[^a-z0-9]+", normalized) if token]


def extract_alias_matches(query: str, alias_map: Dict[str, List[str]]) -> List[str]:
    """Extract canonical labels whose aliases appear in query."""
    normalized_query = normalize_text(query)
    matches: List[str] = []
    for canonical, aliases in alias_map.items():
        for alias in aliases:
            if normalize_text(alias) in normalized_query:
                matches.append(canonical)
                break
    return matches


def normalize_behavior_action(action: str) -> str:
    """Map legacy CSV actions to canonical AI event types."""
    normalized = normalize_text(action).replace(" ", "_")
    aliases = {
        "view": "product_view",
        "click": "product_click",
        "add_to_cart": "add_to_cart",
        "add_to_wishlist": "add_to_wishlist",
        "search": "search",
        "product_view": "product_view",
        "product_click": "product_click",
        "view_category": "view_category",
        "remove_from_cart": "remove_from_cart",
        "checkout_started": "checkout_started",
        "order_created": "order_created",
        "order_cancel": "order_cancel",
        "payment_success": "payment_success",
        "chat_query": "chat_query",
    }
    return aliases.get(normalized, normalized)


def build_taxonomy_terms() -> Set[str]:
    """Return all canonical and alias terms for search enrichment."""
    terms: Set[str] = set()
    for canonical, aliases in {**PRODUCT_GROUP_ALIASES, **CATEGORY_ALIASES}.items():
        terms.add(canonical)
        terms.update(normalize_text(alias) for alias in aliases)
    return terms
