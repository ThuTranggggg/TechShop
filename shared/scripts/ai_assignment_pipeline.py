#!/usr/bin/env python3
"""End-to-end pipeline for the AI assignment deliverables."""

from __future__ import annotations

import argparse
import csv
import html
import json
import logging
import random
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from uuid import NAMESPACE_URL, UUID, uuid5

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "shared" / "generated" / "ai_assignment"
AI_SERVICE_ROOT = REPO_ROOT / "services" / "ai_service"

if str(AI_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_SERVICE_ROOT))

from modules.ai.infrastructure.neo4j_graph import GraphRecord, Neo4jGraphService  # noqa: E402

ACTION_TO_INDEX = {"view": 0, "click": 1, "add_to_cart": 2}
INDEX_TO_ACTION = {index: action for action, index in ACTION_TO_INDEX.items()}

PRICE_BUCKETS: Sequence[Tuple[float, float, str]] = (
    (0, 1_000_000, "under_1m"),
    (1_000_000, 3_000_000, "from_1m_to_3m"),
    (3_000_000, 5_000_000, "from_3m_to_5m"),
    (5_000_000, 10_000_000, "from_5m_to_10m"),
    (10_000_000, 20_000_000, "from_10m_to_20m"),
    (20_000_000, float("inf"), "above_20m"),
)


@dataclass(frozen=True)
class ProductSpec:
    slug: str
    name: str
    brand: str
    category: str
    price: int
    description: str

    @property
    def product_id(self) -> str:
        return str(uuid5(NAMESPACE_URL, f"techshop-product:{self.slug}"))

    @property
    def price_bucket(self) -> str:
        return price_bucket(self.price)


@dataclass(frozen=True)
class BehaviorProfile:
    """A behavior template so the generated dataset has 8 distinct patterns."""

    name: str
    action_weights: Dict[str, float]
    preferred_brands: Tuple[str, ...]
    preferred_categories: Tuple[str, ...]
    preferred_buckets: Tuple[str, ...]
    gap_minutes: Tuple[int, int]
    burst_events: Tuple[int, int]


PRODUCT_CATALOG: Sequence[ProductSpec] = (
    ProductSpec("iphone-15", "iPhone 15", "Apple", "Phone", 19990000, "Flagship phone with A16 performance and solid camera."),
    ProductSpec("iphone-15-pro", "iPhone 15 Pro", "Apple", "Phone", 26990000, "Pro-grade iPhone for creators and heavy users."),
    ProductSpec("iphone-15-pro-max", "iPhone 15 Pro Max", "Apple", "Phone", 32990000, "Large screen and top-end camera system."),
    ProductSpec("macbook-air-m3", "MacBook Air M3", "Apple", "Laptop", 27990000, "Lightweight laptop for students and professionals."),
    ProductSpec("ipad-air-m2", "iPad Air M2", "Apple", "Tablet", 15990000, "Portable tablet for notes, media and sketching."),
    ProductSpec("airpods-pro-2", "AirPods Pro 2", "Apple", "Audio", 6990000, "ANC earbuds with spatial audio."),
    ProductSpec("galaxy-s24", "Galaxy S24", "Samsung", "Phone", 18990000, "Balanced flagship with smart AI features."),
    ProductSpec("galaxy-s24-ultra", "Galaxy S24 Ultra", "Samsung", "Phone", 29990000, "Ultra flagship with S Pen and premium zoom."),
    ProductSpec("galaxy-a55", "Galaxy A55", "Samsung", "Phone", 9990000, "Mid-range phone with strong battery life."),
    ProductSpec("galaxy-tab-s9", "Galaxy Tab S9", "Samsung", "Tablet", 21990000, "Premium Android tablet for work and entertainment."),
    ProductSpec("galaxy-watch7", "Galaxy Watch7", "Samsung", "Wearable", 7990000, "Fitness and health-focused smartwatch."),
    ProductSpec("galaxy-buds3-pro", "Galaxy Buds3 Pro", "Samsung", "Audio", 4990000, "ANC earbuds for Galaxy ecosystem users."),
    ProductSpec("xiaomi-14", "Xiaomi 14", "Xiaomi", "Phone", 17990000, "Compact flagship with Leica-inspired imaging."),
    ProductSpec("redmi-note-13-pro", "Redmi Note 13 Pro", "Xiaomi", "Phone", 7990000, "Value-focused phone with large battery."),
    ProductSpec("xiaomi-pad-6", "Xiaomi Pad 6", "Xiaomi", "Tablet", 10990000, "Slim Android tablet for study and media."),
    ProductSpec("xiaomi-watch-2", "Xiaomi Watch 2", "Xiaomi", "Wearable", 4990000, "Wearable with fitness and sleep tracking."),
    ProductSpec("oppo-reno11", "Oppo Reno11", "Oppo", "Phone", 12990000, "Portrait-centric phone with polished design."),
    ProductSpec("oppo-pad-2", "Oppo Pad 2", "Oppo", "Tablet", 14990000, "Large-screen tablet for productivity."),
    ProductSpec("realme-12-pro-plus", "Realme 12 Pro+", "Realme", "Phone", 10990000, "Camera-first mid-range device."),
    ProductSpec("asus-rog-zephyrus-g14", "ASUS ROG Zephyrus G14", "ASUS", "Laptop", 36990000, "Portable gaming laptop with high-end GPU."),
    ProductSpec("asus-tuf-gaming-a15", "ASUS TUF Gaming A15", "ASUS", "Laptop", 24990000, "Durable gaming laptop with great value."),
    ProductSpec("asus-zenbook-14", "ASUS Zenbook 14", "ASUS", "Laptop", 28990000, "Ultrabook for work and travel."),
    ProductSpec("sony-wh-1000xm5", "Sony WH-1000XM5", "Sony", "Audio", 8990000, "Reference ANC headphones."),
    ProductSpec("playstation-5", "PlayStation 5", "Sony", "Gaming", 13990000, "Console for living-room gaming."),
)

BEHAVIOR_PROFILES: Sequence[BehaviorProfile] = (
    BehaviorProfile(
        "window_shopper",
        {"view": 0.78, "click": 0.18, "add_to_cart": 0.04},
        ("Apple", "Samsung"),
        ("Phone", "Laptop"),
        ("from_10m_to_20m", "above_20m"),
        (30, 180),
        (4, 8),
    ),
    BehaviorProfile(
        "brand_loyalist",
        {"view": 0.62, "click": 0.23, "add_to_cart": 0.15},
        ("Samsung",),
        ("Phone", "Wearable"),
        ("from_5m_to_10m", "from_10m_to_20m"),
        (20, 120),
        (6, 10),
    ),
    BehaviorProfile(
        "spec_researcher",
        {"view": 0.48, "click": 0.40, "add_to_cart": 0.12},
        ("Apple", "ASUS"),
        ("Laptop", "Tablet"),
        ("above_20m", "from_10m_to_20m"),
        (15, 90),
        (8, 12),
    ),
    BehaviorProfile(
        "deal_hunter",
        {"view": 0.66, "click": 0.24, "add_to_cart": 0.10},
        ("Xiaomi", "Realme", "Oppo"),
        ("Phone", "Tablet", "Audio"),
        ("under_1m", "from_1m_to_3m", "from_3m_to_5m", "from_5m_to_10m"),
        (25, 150),
        (5, 9),
    ),
    BehaviorProfile(
        "cart_ready",
        {"view": 0.42, "click": 0.32, "add_to_cart": 0.26},
        ("Apple", "Samsung", "Sony"),
        ("Audio", "Phone", "Gaming"),
        ("from_5m_to_10m", "from_10m_to_20m"),
        (10, 75),
        (7, 11),
    ),
    BehaviorProfile(
        "impulse_buyer",
        {"view": 0.38, "click": 0.24, "add_to_cart": 0.38},
        ("Samsung", "Xiaomi", "Sony"),
        ("Phone", "Audio", "Wearable"),
        ("from_3m_to_5m", "from_5m_to_10m", "from_10m_to_20m"),
        (5, 35),
        (5, 7),
    ),
    BehaviorProfile(
        "premium_upgrade",
        {"view": 0.56, "click": 0.26, "add_to_cart": 0.18},
        ("Apple", "ASUS"),
        ("Phone", "Laptop"),
        ("from_10m_to_20m", "above_20m"),
        (12, 90),
        (6, 10),
    ),
    BehaviorProfile(
        "gaming_spree",
        {"view": 0.50, "click": 0.30, "add_to_cart": 0.20},
        ("ASUS", "Sony"),
        ("Laptop", "Gaming", "Audio"),
        ("from_10m_to_20m", "above_20m"),
        (8, 60),
        (6, 10),
    ),
)


def price_bucket(amount: float) -> str:
    for minimum, maximum, bucket in PRICE_BUCKETS:
        if minimum <= amount < maximum:
            return bucket
    return "above_20m"


def user_id_for_index(index: int) -> str:
    return str(uuid5(NAMESPACE_URL, f"techshop-user:{index:04d}"))


def product_lookup() -> Dict[str, ProductSpec]:
    return {product.product_id: product for product in PRODUCT_CATALOG}


def weighted_choice(rng: random.Random, items: Sequence[Any], weights: Sequence[float]) -> Any:
    return rng.choices(list(items), weights=list(weights), k=1)[0]


def choose_product(rng: random.Random, profile: BehaviorProfile, action: str) -> ProductSpec:
    options = list(PRODUCT_CATALOG)
    weights: List[float] = []
    for product in options:
        weight = 1.0
        if product.brand in profile.preferred_brands:
            weight *= 3.0
        if product.category in profile.preferred_categories:
            weight *= 2.5
        if product.price_bucket in profile.preferred_buckets:
            weight *= 2.2
        if action == "add_to_cart" and product.price_bucket in {"from_3m_to_5m", "from_5m_to_10m", "from_10m_to_20m"}:
            weight *= 1.7
        if action == "click" and product.category in profile.preferred_categories:
            weight *= 1.4
        weights.append(weight)
    return weighted_choice(rng, options, weights)


def build_dataset_rows(
    *,
    num_users: int,
    min_events: int,
    max_events: int,
    seed: int,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Any], Dict[str, str]]:
    rng = random.Random(seed)
    rows: List[Dict[str, Any]] = []
    user_profiles: Dict[str, str] = {}
    summary = {
        "users": num_users,
        "events": 0,
        "profiles": Counter(),
        "actions": Counter(),
        "price_buckets": Counter(),
    }

    profile_cycle = list(BEHAVIOR_PROFILES)
    for user_index in range(num_users):
        profile = profile_cycle[user_index % len(profile_cycle)]
        user_id = user_id_for_index(user_index)
        user_profiles[user_id] = profile.name
        summary["profiles"][profile.name] += 1

        user_rng = random.Random(seed + user_index * 31)
        event_count = user_rng.randint(min_events, max_events)
        burst_count = user_rng.randint(*profile.burst_events)
        start_time = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=user_index % 28)
        current_time = start_time + timedelta(minutes=user_rng.randint(0, 240))

        for event_index in range(event_count):
            action = weighted_choice(user_rng, list(profile.action_weights.keys()), list(profile.action_weights.values()))
            product = choose_product(user_rng, profile, action)
            if event_index and event_index % burst_count == 0:
                current_time += timedelta(minutes=user_rng.randint(1, 15))
            else:
                current_time += timedelta(minutes=user_rng.randint(*profile.gap_minutes))

            row = {
                "user_id": user_id,
                "product_id": product.product_id,
                "action": action,
                "timestamp": current_time.isoformat().replace("+00:00", "Z"),
                "product_name": product.name,
                "brand_name": product.brand,
                "category_name": product.category,
                "price_amount": product.price,
                "price_bucket": product.price_bucket,
                "behavior_profile": profile.name,
            }
            rows.append(row)
            summary["events"] += 1
            summary["actions"][action] += 1
            summary["price_buckets"][product.price_bucket] += 1

    rows.sort(key=lambda item: (item["timestamp"], item["user_id"], item["product_id"]))
    return rows, summary, {product.product_id: asdict_product(product) for product in PRODUCT_CATALOG}, user_profiles


def asdict_product(product: ProductSpec) -> Dict[str, Any]:
    return {
        "product_id": product.product_id,
        "slug": product.slug,
        "name": product.name,
        "brand": product.brand,
        "category": product.category,
        "price": product.price,
        "price_bucket": product.price_bucket,
        "description": product.description,
    }


def write_csv(path: Path, rows: Sequence[Dict[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_preview_csv(path: Path, rows: Sequence[Dict[str, Any]], limit: int = 20) -> None:
    preview_fields = ["user_id", "product_id", "action", "timestamp"]
    write_csv(path, list(rows)[:limit], preview_fields)


def summarize_dataset(rows: Sequence[Dict[str, Any]], summary: Dict[str, Any], output_dir: Path) -> Dict[str, Any]:
    payload = {
        "users": summary["users"],
        "events": summary["events"],
        "profile_counts": dict(summary["profiles"]),
        "action_counts": dict(summary["actions"]),
        "price_bucket_counts": dict(summary["price_buckets"]),
        "product_catalog_size": len(PRODUCT_CATALOG),
        "first_timestamp": rows[0]["timestamp"] if rows else None,
        "last_timestamp": rows[-1]["timestamp"] if rows else None,
    }
    write_json(output_dir / "dataset_summary.json", payload)
    return payload


def plot_bar_chart(path: Path, title: str, labels: Sequence[str], values: Sequence[int], color: str) -> None:
    width, height = 1200, 700
    margin = 80
    plot_w = width - margin * 2
    plot_h = height - margin * 2
    max_value = max(values) if values else 1
    bar_slot = plot_w / max(len(values), 1)
    bar_width = bar_slot * 0.68

    bars = []
    for index, (label, value) in enumerate(zip(labels, values)):
        bar_height = 0 if max_value == 0 else (value / max_value) * plot_h
        x = margin + index * bar_slot + (bar_slot - bar_width) / 2
        y = height - margin - bar_height
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" rx="18" fill="{color}" />'
        )
        bars.append(
            f'<text x="{x + bar_width / 2:.1f}" y="{height - margin + 28}" text-anchor="middle" font-size="22" fill="#334155">{label}</text>'
        )
        bars.append(
            f'<text x="{x + bar_width / 2:.1f}" y="{y - 12:.1f}" text-anchor="middle" font-size="20" font-weight="700" fill="#0f172a">{value}</text>'
        )

    grid = []
    for tick in range(5):
        y = height - margin - (plot_h / 4) * tick
        grid.append(f'<line x1="{margin}" y1="{y:.1f}" x2="{width - margin}" y2="{y:.1f}" stroke="#e2e8f0" stroke-width="2" />')
        grid.append(
            f'<text x="{margin - 18}" y="{y + 6:.1f}" text-anchor="end" font-size="18" fill="#64748b">{int(max_value * tick / 4)}</text>'
        )

    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
      <rect width="100%" height="100%" fill="#ffffff" />
      <text x="{margin}" y="48" font-size="28" font-weight="800" fill="#0f172a">{title}</text>
      {''.join(grid)}
      {''.join(bars)}
    </svg>
    """
    path.write_text(svg.strip(), encoding="utf-8")


def plot_line_chart(path: Path, title: str, history: Sequence[Dict[str, float]]) -> None:
    width, height = 1200, 700
    margin = 90
    plot_w = width - margin * 2
    plot_h = height - margin * 2
    metrics = {
        "train_loss": [float(point["train_loss"]) for point in history],
        "val_loss": [float(point["val_loss"]) for point in history],
        "val_accuracy": [float(point["val_accuracy"]) for point in history],
        "val_macro_f1": [float(point["val_macro_f1"]) for point in history],
    }
    max_loss = max(metrics["train_loss"] + metrics["val_loss"] + [1.0])
    epochs = list(range(1, len(history) + 1))
    x_step = plot_w / max(len(epochs) - 1, 1)

    def line_points(values: Sequence[float], invert: bool = False) -> str:
        points = []
        for index, value in enumerate(values):
            x = margin + index * x_step
            if invert:
                y = height - margin - (value * plot_h)
            else:
                y = height - margin - (value / max_loss) * plot_h
            points.append(f"{x:.1f},{y:.1f}")
        return " ".join(points)

    loss_poly = line_points(metrics["train_loss"])
    val_loss_poly = line_points(metrics["val_loss"])
    acc_poly = line_points(metrics["val_accuracy"], invert=True)
    f1_poly = line_points(metrics["val_macro_f1"], invert=True)

    axes = [
        f'<line x1="{margin}" y1="{height - margin}" x2="{width - margin}" y2="{height - margin}" stroke="#94a3b8" stroke-width="2" />',
        f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height - margin}" stroke="#94a3b8" stroke-width="2" />',
    ]
    legend = [
        ('train loss', '#0ea5e9'),
        ('val loss', '#f97316'),
        ('val acc', '#10b981'),
        ('val macro F1', '#8b5cf6'),
    ]
    legend_svg = []
    for index, (label, color) in enumerate(legend):
        x = margin + index * 220
        legend_svg.append(f'<rect x="{x}" y="58" width="18" height="18" rx="4" fill="{color}" />')
        legend_svg.append(f'<text x="{x + 26}" y="73" font-size="18" fill="#334155">{label}</text>')

    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
      <rect width="100%" height="100%" fill="#ffffff" />
      <text x="{margin}" y="36" font-size="28" font-weight="800" fill="#0f172a">{title}</text>
      {''.join(axes)}
      {''.join(legend_svg)}
      <polyline points="{loss_poly}" fill="none" stroke="#0ea5e9" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />
      <polyline points="{val_loss_poly}" fill="none" stroke="#f97316" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />
      <polyline points="{acc_poly}" fill="none" stroke="#10b981" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />
      <polyline points="{f1_poly}" fill="none" stroke="#8b5cf6" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />
    </svg>
    """
    path.write_text(svg.strip(), encoding="utf-8")


def plot_confusion_matrix(path: Path, title: str, matrix: Sequence[Sequence[int]], labels: Sequence[str]) -> None:
    size = 860
    margin = 110
    cell = (size - margin * 2) / max(len(labels), 1)
    max_value = max((value for row in matrix for value in row), default=1)
    cells = []
    for row_index, row in enumerate(matrix):
        for col_index, value in enumerate(row):
            intensity = 30 + int(200 * (value / max_value if max_value else 0))
            x = margin + col_index * cell
            y = margin + row_index * cell
            cells.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell:.1f}" height="{cell:.1f}" fill="rgb(37,{intensity},122)" stroke="#ffffff" stroke-width="2" />')
            cells.append(
                f'<text x="{x + cell / 2:.1f}" y="{y + cell / 2 + 8:.1f}" text-anchor="middle" font-size="20" font-weight="700" fill="#ffffff">{value}</text>'
            )

    axis_labels = []
    for index, label in enumerate(labels):
        x = margin + index * cell + cell / 2
        axis_labels.append(f'<text x="{x:.1f}" y="{margin - 22}" text-anchor="middle" font-size="18" fill="#334155">{label}</text>')
        y = margin + index * cell + cell / 2 + 6
        axis_labels.append(f'<text x="{margin - 22}" y="{y:.1f}" text-anchor="end" font-size="18" fill="#334155">{label}</text>')

    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">
      <rect width="100%" height="100%" fill="#ffffff" />
      <text x="{margin}" y="42" font-size="28" font-weight="800" fill="#0f172a">{title}</text>
      <text x="36" y="{size / 2:.1f}" transform="rotate(-90 36 {size / 2:.1f})" font-size="20" fill="#475569">Actual</text>
      <text x="{size / 2:.1f}" y="{size - 28}" text-anchor="middle" font-size="20" fill="#475569">Predicted</text>
      {''.join(cells)}
      {''.join(axis_labels)}
    </svg>
    """
    path.write_text(svg.strip(), encoding="utf-8")


def generate_dataset(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    num_users: int = 500,
    min_events: int = 32,
    max_events: int = 60,
    seed: int = 42,
) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows, summary, catalog, user_profiles = build_dataset_rows(
        num_users=num_users,
        min_events=min_events,
        max_events=max_events,
        seed=seed,
    )

    data_csv = output_dir / "data_user500.csv"
    preview_csv = output_dir / "data_user500_preview.csv"
    catalog_json = output_dir / "product_catalog.json"
    profiles_json = output_dir / "behavior_profiles.json"
    summary_json = output_dir / "dataset_summary.json"
    write_csv(
        data_csv,
        rows,
        ["user_id", "product_id", "action", "timestamp"],
    )
    write_preview_csv(preview_csv, rows, limit=20)
    write_json(catalog_json, list(catalog.values()))
    write_json(profiles_json, user_profiles)
    dataset_summary = summarize_dataset(rows, summary, output_dir)

    action_items = sorted(summary["actions"].items(), key=lambda item: item[0])
    plot_bar_chart(
        output_dir / "actions_distribution.svg",
        "Action Distribution",
        [action for action, _ in action_items],
        [count for _, count in action_items],
        "#0ea5e9",
    )
    plot_bar_chart(
        output_dir / "profiles_distribution.svg",
        "Behavior Profile Distribution",
        [profile.name for profile in BEHAVIOR_PROFILES],
        [summary["profiles"][profile.name] for profile in BEHAVIOR_PROFILES],
        "#8b5cf6",
    )

    return {
        "rows": rows,
        "dataset_summary": dataset_summary,
        "data_csv": data_csv,
        "preview_csv": preview_csv,
        "product_catalog": catalog_json,
        "profiles": profiles_json,
        "summary": summary_json,
    }


def load_rows(csv_path: Path) -> List[Dict[str, str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def _require_torch():
    try:
        import torch  # type: ignore
    except ImportError as exc:  # pragma: no cover - hard dependency for train command
        raise RuntimeError(
            "torch is required for the training step. Install from shared/requirements-ai-assignment.txt."
        ) from exc
    return torch


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def split_users(user_ids: Sequence[str], seed: int) -> Tuple[List[str], List[str], List[str]]:
    shuffled = list(user_ids)
    rng = random.Random(seed)
    rng.shuffle(shuffled)
    train_end = int(len(shuffled) * 0.7)
    val_end = int(len(shuffled) * 0.85)
    return shuffled[:train_end], shuffled[train_end:val_end], shuffled[val_end:]


def build_sequence_samples(rows: Sequence[Dict[str, str]], seq_len: int) -> List[Dict[str, Any]]:
    by_user: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_user[row["user_id"]].append(row)

    samples: List[Dict[str, Any]] = []
    for user_id, events in by_user.items():
        ordered = sorted(events, key=lambda item: item["timestamp"])
        actions = [ACTION_TO_INDEX[item["action"]] + 1 for item in ordered]
        timestamps = [_parse_timestamp(item["timestamp"]) for item in ordered]
        if len(actions) <= seq_len:
            continue
        for index in range(seq_len, len(actions)):
            window_actions = actions[index - seq_len : index]
            window_times = timestamps[index - seq_len : index]
            gaps = [0.0]
            for step in range(1, len(window_times)):
                gap_hours = (window_times[step] - window_times[step - 1]).total_seconds() / 3600.0
                gaps.append(min(gap_hours, 24.0) / 24.0)
            samples.append(
                {
                    "user_id": user_id,
                    "actions": window_actions,
                    "gaps": gaps,
                    "target": ACTION_TO_INDEX[ordered[index]["action"]],
                }
            )
    return samples


def compute_metrics(y_true: Sequence[int], y_pred: Sequence[int], num_classes: int = 3) -> Dict[str, Any]:
    matrix = [[0 for _ in range(num_classes)] for _ in range(num_classes)]
    for actual, predicted in zip(y_true, y_pred):
        matrix[actual][predicted] += 1

    total = len(y_true) or 1
    accuracy = sum(matrix[i][i] for i in range(num_classes)) / total
    precisions: List[float] = []
    recalls: List[float] = []
    f1s: List[float] = []
    for index in range(num_classes):
        tp = matrix[index][index]
        fp = sum(matrix[row][index] for row in range(num_classes)) - tp
        fn = sum(matrix[index][col] for col in range(num_classes)) - tp
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        precisions.append(precision)
        recalls.append(recall)
        f1s.append(f1)

    return {
        "accuracy": accuracy,
        "macro_precision": float(sum(precisions) / num_classes),
        "macro_recall": float(sum(recalls) / num_classes),
        "macro_f1": float(sum(f1s) / num_classes),
        "confusion_matrix": matrix,
    }


def to_tensor_batches(torch, arrays: Dict[str, np.ndarray], batch_size: int, shuffle: bool = False):
    dataset = torch.utils.data.TensorDataset(
        torch.tensor(arrays["actions"], dtype=torch.long),
        torch.tensor(arrays["gaps"], dtype=torch.float32),
        torch.tensor(arrays["targets"], dtype=torch.long),
    )
    return torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)


def build_arrays(samples: Sequence[Dict[str, Any]], user_ids: Sequence[str], seq_len: int) -> Dict[str, np.ndarray]:
    selected = [sample for sample in samples if sample["user_id"] in set(user_ids)]
    if not selected:
        return {
            "actions": np.zeros((0, seq_len), dtype=np.int64),
            "gaps": np.zeros((0, seq_len), dtype=np.float32),
            "targets": np.zeros((0,), dtype=np.int64),
        }
    actions = np.asarray([sample["actions"] for sample in selected], dtype=np.int64)
    gaps = np.asarray([sample["gaps"] for sample in selected], dtype=np.float32)
    targets = np.asarray([sample["target"] for sample in selected], dtype=np.int64)
    return {"actions": actions, "gaps": gaps, "targets": targets}


def class_weights_from_targets(targets: np.ndarray, num_classes: int = 3):
    counts = np.bincount(targets, minlength=num_classes)
    counts = np.where(counts == 0, 1, counts)
    weights = counts.sum() / (num_classes * counts)
    return weights.astype(np.float32)


class SequenceClassifier:
    """Torch model wrapper kept here so the script stays importable without torch installed."""

    def __init__(self, torch, model_type: str, seq_len: int, num_classes: int = 3):
        self.torch = torch
        hidden_size = 48
        emb_dim = 12
        self.model_type = model_type
        self.seq_len = seq_len
        self.num_classes = num_classes

        class _Net(torch.nn.Module):
            def __init__(self, cell_type: str):
                super().__init__()
                self.embedding = torch.nn.Embedding(4, emb_dim, padding_idx=0)
                self.cell_type = cell_type
                rnn_kwargs = {
                    "input_size": emb_dim + 1,
                    "hidden_size": hidden_size,
                    "batch_first": True,
                }
                if cell_type == "rnn":
                    self.sequence = torch.nn.RNN(**rnn_kwargs)
                elif cell_type == "lstm":
                    self.sequence = torch.nn.LSTM(**rnn_kwargs)
                elif cell_type == "bilstm":
                    self.sequence = torch.nn.LSTM(**rnn_kwargs, bidirectional=True)
                else:
                    raise ValueError(f"Unknown model type: {cell_type}")
                direction_factor = 2 if cell_type == "bilstm" else 1
                self.head = torch.nn.Sequential(
                    torch.nn.Linear(hidden_size * direction_factor + 1, 64),
                    torch.nn.ReLU(),
                    torch.nn.Dropout(0.15),
                    torch.nn.Linear(64, num_classes),
                )

            def forward(self, actions, gaps):
                embeddings = self.embedding(actions)
                x = torch.cat([embeddings, gaps.unsqueeze(-1)], dim=-1)
                outputs, _ = self.sequence(x)
                summary = outputs[:, -1, :]
                gap_mean = gaps.mean(dim=1, keepdim=True)
                logits = self.head(torch.cat([summary, gap_mean], dim=-1))
                return logits

        self.net = _Net(model_type)

    def parameters(self):
        return self.net.parameters()

    def train(self):
        self.net.train()

    def eval(self):
        self.net.eval()

    def state_dict(self):
        return self.net.state_dict()

    def load_state_dict(self, state):
        self.net.load_state_dict(state)

    def __call__(self, actions, gaps):
        return self.net(actions, gaps)


def run_training_epoch(torch, model: SequenceClassifier, loader, optimizer, criterion):
    model.train()
    losses = []
    for actions, gaps, targets in loader:
        optimizer.zero_grad(set_to_none=True)
        logits = model(actions, gaps)
        loss = criterion(logits, targets)
        loss.backward()
        optimizer.step()
        losses.append(float(loss.detach().cpu().item()))
    return float(sum(losses) / max(len(losses), 1))


def evaluate_model(torch, model: SequenceClassifier, loader):
    model.eval()
    all_targets: List[int] = []
    all_predictions: List[int] = []
    losses: List[float] = []
    criterion = torch.nn.CrossEntropyLoss()
    with torch.no_grad():
        for actions, gaps, targets in loader:
            logits = model(actions, gaps)
            loss = criterion(logits, targets)
            predictions = torch.argmax(logits, dim=1)
            losses.append(float(loss.detach().cpu().item()))
            all_targets.extend(targets.cpu().numpy().tolist())
            all_predictions.extend(predictions.cpu().numpy().tolist())
    metrics = compute_metrics(all_targets, all_predictions)
    metrics["loss"] = float(sum(losses) / max(len(losses), 1))
    metrics["targets"] = all_targets
    metrics["predictions"] = all_predictions
    return metrics


def train_models(
    *,
    csv_path: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    seq_len: int = 12,
    seed: int = 42,
    epochs: int = 10,
    batch_size: int = 128,
) -> Dict[str, Any]:
    torch = _require_torch()
    output_dir.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)

    rows = load_rows(csv_path)
    samples = build_sequence_samples(rows, seq_len=seq_len)
    user_ids = sorted({sample["user_id"] for sample in samples})
    train_users, val_users, test_users = split_users(user_ids, seed=seed)

    train_arrays = build_arrays(samples, train_users, seq_len)
    val_arrays = build_arrays(samples, val_users, seq_len)
    test_arrays = build_arrays(samples, test_users, seq_len)

    train_loader = to_tensor_batches(torch, train_arrays, batch_size=batch_size, shuffle=True)
    val_loader = to_tensor_batches(torch, val_arrays, batch_size=batch_size, shuffle=False)
    test_loader = to_tensor_batches(torch, test_arrays, batch_size=batch_size, shuffle=False)

    class_weights = torch.tensor(class_weights_from_targets(train_arrays["targets"]), dtype=torch.float32)
    criterion = torch.nn.CrossEntropyLoss(weight=class_weights)

    results: Dict[str, Any] = {
        "seq_len": seq_len,
        "split": {
            "train_users": len(train_users),
            "val_users": len(val_users),
            "test_users": len(test_users),
            "train_samples": int(len(train_arrays["targets"])),
            "val_samples": int(len(val_arrays["targets"])),
            "test_samples": int(len(test_arrays["targets"])),
        },
        "models": {},
    }

    best_model_name: Optional[str] = None
    best_model_score = -1.0
    best_state: Optional[Dict[str, Any]] = None

    for model_name in ["rnn", "lstm", "bilstm"]:
        model = SequenceClassifier(torch, model_name, seq_len=seq_len)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=1e-4)
        history: List[Dict[str, float]] = []
        best_val_score = -1.0
        best_val_state = None
        best_val_loss = None
        patience = 3
        stalled = 0

        for _epoch in range(epochs):
            train_loss = run_training_epoch(torch, model, train_loader, optimizer, criterion)
            val_metrics = evaluate_model(torch, model, val_loader)
            history.append(
                {
                    "train_loss": train_loss,
                    "val_loss": float(val_metrics["loss"]),
                    "val_accuracy": float(val_metrics["accuracy"]),
                    "val_macro_f1": float(val_metrics["macro_f1"]),
                }
            )

            if val_metrics["macro_f1"] > best_val_score:
                best_val_score = float(val_metrics["macro_f1"])
                best_val_loss = float(val_metrics["loss"])
                best_val_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
                stalled = 0
            else:
                stalled += 1
                if stalled >= patience:
                    break

        if best_val_state is not None:
            model.load_state_dict(best_val_state)

        test_metrics = evaluate_model(torch, model, test_loader)
        model_path = output_dir / f"{model_name}.pt"
        torch.save(model.state_dict(), model_path)

        results["models"][model_name] = {
            "history": history,
            "validation": {
                "loss": best_val_loss,
                "macro_f1": best_val_score,
            },
            "test": {
                "accuracy": float(test_metrics["accuracy"]),
                "macro_precision": float(test_metrics["macro_precision"]),
                "macro_recall": float(test_metrics["macro_recall"]),
                "macro_f1": float(test_metrics["macro_f1"]),
                "confusion_matrix": test_metrics["confusion_matrix"],
                "predictions": test_metrics["predictions"],
                "targets": test_metrics["targets"],
            },
            "artifact": str(model_path),
        }

        plot_line_chart(output_dir / f"{model_name}_learning_curve.svg", f"{model_name.upper()} learning curve", history)

        if best_val_score > best_model_score:
            best_model_score = float(best_val_score)
            best_model_name = model_name
            best_state = best_val_state

    if not best_model_name or best_state is None:
        raise RuntimeError("No model could be trained")

    best_model_path = output_dir / "model_best.pt"
    torch.save(best_state, best_model_path)
    best_metrics = results["models"][best_model_name]["test"]
    plot_confusion_matrix(
        output_dir / "model_best_confusion_matrix.svg",
        f"Best model confusion matrix ({best_model_name.upper()})",
        best_metrics["confusion_matrix"],
        ["view", "click", "add_to_cart"],
    )

    comparison = {
        model_name: round(metrics["test"]["macro_f1"] * 100) for model_name, metrics in results["models"].items()
    }
    plot_bar_chart(
        output_dir / "model_comparison.svg",
        "Model comparison by macro F1 (%)",
        list(comparison.keys()),
        list(comparison.values()),
        "#16a34a",
    )

    results["best_model"] = {
        "name": best_model_name,
        "macro_f1": best_model_score,
        "artifact": str(best_model_path),
        "comparison": comparison,
    }
    write_json(output_dir / "training_results.json", results)
    return results


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def build_graph_records(
    rows: Sequence[Dict[str, str]],
    catalog_by_id: Dict[str, Dict[str, Any]],
    user_profiles: Dict[str, str],
) -> List[GraphRecord]:
    records: List[GraphRecord] = []
    for row in rows:
        product = catalog_by_id.get(row["product_id"], {})
        records.append(
            GraphRecord(
                user_id=row["user_id"],
                product_id=row["product_id"],
                action=row["action"],
                timestamp=row["timestamp"],
                product_name=product.get("name", ""),
                brand_name=product.get("brand", ""),
                category_name=product.get("category", ""),
                price_amount=float(product.get("price", 0) or 0),
                behavior_profile=user_profiles.get(row["user_id"], "unclassified"),
            )
        )
    return records


def truncate_label(value: str, limit: int = 18) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 1] + "…"


def render_graph_preview_svg(
    path: Path,
    *,
    records: Sequence[GraphRecord],
    catalog_by_id: Dict[str, Dict[str, Any]],
    user_profiles: Dict[str, str],
) -> None:
    width, height = 1800, 1300
    margin = 70
    profiles = [profile.name for profile in BEHAVIOR_PROFILES]
    users_by_profile: Dict[str, List[str]] = defaultdict(list)
    for record in records:
        bucket = users_by_profile[record.behavior_profile]
        if record.user_id not in bucket:
            bucket.append(record.user_id)

    sampled_users: List[str] = []
    for profile in profiles:
        if users_by_profile.get(profile):
            sampled_users.append(users_by_profile[profile][0])
    for record in records:
        if record.user_id not in sampled_users:
            sampled_users.append(record.user_id)
        if len(sampled_users) >= 12:
            break

    product_freq = Counter(record.product_id for record in records).most_common(12)
    sampled_products = [product_id for product_id, _ in product_freq]
    brands = []
    categories = []
    for product_id in sampled_products:
        product = catalog_by_id.get(product_id, {})
        if product.get("brand") and product["brand"] not in brands:
            brands.append(product["brand"])
        if product.get("category") and product["category"] not in categories:
            categories.append(product["category"])

    positions: Dict[Tuple[str, str], Tuple[float, float]] = {}
    node_lines: List[str] = []
    edge_lines: List[str] = []

    def place_nodes(items: Sequence[str], x: float, top: float, bottom: float, kind: str, fill: str) -> None:
        if not items:
            return
        step = (bottom - top) / max(len(items) - 1, 1)
        for index, item in enumerate(items):
            y = top + index * step
            positions[(kind, item)] = (x, y)
            node_lines.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="42" fill="{fill}" stroke="#ffffff" stroke-width="4" />'
            )
            node_lines.append(
                f'<text x="{x:.1f}" y="{y + 6:.1f}" text-anchor="middle" font-size="16" font-weight="700" fill="#ffffff">{html.escape(truncate_label(item, 14))}</text>'
            )

    place_nodes(profiles, 180, 120, height - 120, "profile", "#8b5cf6")
    place_nodes(sampled_users, 560, 170, height - 170, "user", "#0ea5e9")
    place_nodes(sampled_products, 1090, 140, height - 140, "product", "#16a34a")
    place_nodes(brands, 1470, 220, 420, "brand", "#f97316")
    place_nodes(categories, 1470, 700, 920, "category", "#334155")

    seen_edges = set()
    for record in records:
        if record.user_id not in sampled_users or record.product_id not in sampled_products:
            continue
        user_pos = positions.get(("user", record.user_id))
        product_pos = positions.get(("product", record.product_id))
        profile_pos = positions.get(("profile", record.behavior_profile))
        brand_pos = positions.get(("brand", record.brand_name))
        category_pos = positions.get(("category", record.category_name))
        if user_pos and product_pos:
            edge_key = (user_pos, product_pos, record.action)
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                stroke = {"view": "#38bdf8", "click": "#8b5cf6", "add_to_cart": "#f97316"}.get(record.action, "#94a3b8")
                edge_lines.append(
                    f'<line x1="{user_pos[0]:.1f}" y1="{user_pos[1]:.1f}" x2="{product_pos[0]:.1f}" y2="{product_pos[1]:.1f}" stroke="{stroke}" stroke-opacity="0.25" stroke-width="3" />'
                )
        if profile_pos and user_pos:
            edge_key = (profile_pos, user_pos, "profile")
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                edge_lines.append(
                    f'<line x1="{profile_pos[0]:.1f}" y1="{profile_pos[1]:.1f}" x2="{user_pos[0]:.1f}" y2="{user_pos[1]:.1f}" stroke="#8b5cf6" stroke-opacity="0.2" stroke-width="2" />'
                )
        if product_pos and brand_pos:
            edge_key = (product_pos, brand_pos, "brand")
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                edge_lines.append(
                    f'<line x1="{product_pos[0]:.1f}" y1="{product_pos[1]:.1f}" x2="{brand_pos[0]:.1f}" y2="{brand_pos[1]:.1f}" stroke="#f97316" stroke-opacity="0.18" stroke-width="2" />'
                )
        if product_pos and category_pos:
            edge_key = (product_pos, category_pos, "category")
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                edge_lines.append(
                    f'<line x1="{product_pos[0]:.1f}" y1="{product_pos[1]:.1f}" x2="{category_pos[0]:.1f}" y2="{category_pos[1]:.1f}" stroke="#334155" stroke-opacity="0.18" stroke-width="2" />'
                )

    title = "KB_Graph | TechShop behavioral knowledge graph"
    legend = """
      <g>
        <rect x="70" y="38" width="16" height="16" rx="4" fill="#8b5cf6" />
        <text x="94" y="52" font-size="16" fill="#334155">Behavior profile</text>
        <rect x="250" y="38" width="16" height="16" rx="4" fill="#0ea5e9" />
        <text x="274" y="52" font-size="16" fill="#334155">User</text>
        <rect x="340" y="38" width="16" height="16" rx="4" fill="#16a34a" />
        <text x="364" y="52" font-size="16" fill="#334155">Product</text>
        <rect x="450" y="38" width="16" height="16" rx="4" fill="#f97316" />
        <text x="474" y="52" font-size="16" fill="#334155">Brand</text>
        <rect x="530" y="38" width="16" height="16" rx="4" fill="#334155" />
        <text x="554" y="52" font-size="16" fill="#334155">Category</text>
      </g>
    """

    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
      <defs>
        <filter id="softShadow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="14" stdDeviation="18" flood-color="#0f172a" flood-opacity="0.12" />
        </filter>
      </defs>
      <rect width="100%" height="100%" fill="#f8fafc" />
      <rect x="40" y="24" width="{width - 80}" height="{height - 60}" rx="36" fill="#ffffff" filter="url(#softShadow)" />
      <text x="70" y="92" font-size="30" font-weight="800" fill="#0f172a">{title}</text>
      {legend}
      {''.join(edge_lines)}
      {''.join(node_lines)}
    </svg>
    """
    path.write_text(svg.strip(), encoding="utf-8")


def write_sample_queries(path: Path) -> None:
    path.write_text(
        """
// Inspect the full behavioral graph
MATCH (u:User)-[r:VIEWED|CLICKED|ADDED_TO_CART]->(p:Product)
RETURN u.user_id AS user_id, type(r) AS action, p.product_id AS product_id, count(*) AS interactions
ORDER BY interactions DESC
LIMIT 50;

// Brand and category structure for a specific user
MATCH (u:User {user_id: $user_id})-[r:VIEWED|CLICKED|ADDED_TO_CART]->(p:Product)
OPTIONAL MATCH (p)-[:IN_BRAND]->(b:Brand)
OPTIONAL MATCH (p)-[:IN_CATEGORY]->(c:Category)
RETURN b.name AS brand, c.name AS category, count(r) AS interactions
ORDER BY interactions DESC;

// Related products for one item
MATCH (p:Product {product_id: $product_id})<-[:VIEWED|CLICKED|ADDED_TO_CART]-(u:User)-[r:VIEWED|CLICKED|ADDED_TO_CART]->(related:Product)
WHERE related.product_id <> $product_id
RETURN related.product_id AS product_id, count(r) AS score
ORDER BY score DESC
LIMIT 10;
""".strip(),
        encoding="utf-8",
    )


def markdown_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    escaped_headers = [str(header).replace("|", "\\|") for header in headers]
    lines = [
        "| " + " | ".join(escaped_headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        escaped_row = [str(cell).replace("|", "\\|") for cell in row]
        lines.append("| " + " | ".join(escaped_row) + " |")
    return "\n".join(lines)


def render_rows_table_svg(path: Path, rows: Sequence[Dict[str, str]], title: str) -> None:
    width = 1620
    header_h = 72
    row_h = 34
    margin = 32
    table_w = width - margin * 2
    col_widths = [430, 430, 170, 520]
    x_positions = [margin]
    for width_part in col_widths[:-1]:
        x_positions.append(x_positions[-1] + width_part)
    height = margin * 2 + header_h + row_h * len(rows) + 26

    def cell_text(value: str, x: float, y: float, font_size: int = 18, weight: int = 400) -> str:
        return (
            f'<text x="{x:.1f}" y="{y:.1f}" font-size="{font_size}" font-weight="{weight}" '
            f'fill="#0f172a">{html.escape(value)}</text>'
        )

    header = [
        f'<rect x="{margin}" y="{margin}" width="{table_w}" height="{header_h}" rx="16" fill="#0f172a" />',
        cell_text("user_id", x_positions[0] + 16, margin + 44, 18, 700),
        cell_text("product_id", x_positions[1] + 16, margin + 44, 18, 700),
        cell_text("action", x_positions[2] + 16, margin + 44, 18, 700),
        cell_text("timestamp", x_positions[3] + 16, margin + 44, 18, 700),
    ]

    body: List[str] = []
    for index, row in enumerate(rows):
        y = margin + header_h + index * row_h
        fill = "#ffffff" if index % 2 == 0 else "#f8fafc"
        body.append(
            f'<rect x="{margin}" y="{y}" width="{table_w}" height="{row_h}" fill="{fill}" stroke="#e2e8f0" stroke-width="1" />'
        )
        body.append(cell_text(row["user_id"], x_positions[0] + 16, y + 22))
        body.append(cell_text(row["product_id"], x_positions[1] + 16, y + 22))
        body.append(cell_text(row["action"], x_positions[2] + 16, y + 22))
        body.append(cell_text(row["timestamp"], x_positions[3] + 16, y + 22))

    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
      <rect width="100%" height="100%" fill="#f8fafc" />
      <rect x="{margin - 8}" y="{margin - 8}" width="{table_w + 16}" height="{height - margin * 2 + 16}" rx="24" fill="#ffffff" stroke="#e2e8f0" stroke-width="2" />
      <text x="{margin}" y="26" font-size="28" font-weight="800" fill="#0f172a">{html.escape(title)}</text>
      {''.join(header)}
      {''.join(body)}
    </svg>
    """
    path.write_text(svg.strip(), encoding="utf-8")


def render_flow_diagram_svg(
    path: Path,
    *,
    title: str,
    subtitle: str,
    steps: Sequence[Tuple[str, str, str]],
) -> None:
    width = 1720
    height = 620
    margin = 64
    slot = (width - margin * 2) / max(len(steps), 1)
    box_w = min(240, slot - 20)
    box_h = 128
    center_y = 286

    def multiline_text(label: str, x: float, y: float, color: str) -> str:
        parts = label.split("\n")
        lines = []
        for index, part in enumerate(parts):
            dy = 0 if index == 0 else 24
            weight = 700 if index == 0 else 400
            size = 20 if index == 0 else 16
            lines.append(
                f'<tspan x="{x:.1f}" dy="{dy}" font-size="{size}" font-weight="{weight}" fill="{color}">{html.escape(part)}</tspan>'
            )
        return f'<text text-anchor="middle" x="{x:.1f}" y="{y:.1f}">{"".join(lines)}</text>'

    defs = """
      <defs>
        <marker id="arrowHead" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto">
          <path d="M 0 0 L 12 6 L 0 12 z" fill="#64748b" />
        </marker>
      </defs>
    """

    nodes: List[str] = []
    arrows: List[str] = []
    for index, (label, caption, color) in enumerate(steps):
        cx = margin + index * slot + slot / 2
        x = cx - box_w / 2
        nodes.append(
            f'<rect x="{x:.1f}" y="{center_y - box_h / 2:.1f}" width="{box_w:.1f}" height="{box_h:.1f}" rx="22" fill="{color}" stroke="#ffffff" stroke-width="3" filter="url(#shadow)" />'
        )
        nodes.append(multiline_text(label, cx, center_y - 10, "#ffffff"))
        nodes.append(
            f'<text x="{cx:.1f}" y="{center_y + 34}" text-anchor="middle" font-size="14" fill="rgba(255,255,255,0.92)">{html.escape(caption)}</text>'
        )
        if index < len(steps) - 1:
            next_cx = margin + (index + 1) * slot + slot / 2
            arrows.append(
                f'<line x1="{x + box_w:.1f}" y1="{center_y:.1f}" x2="{next_cx - box_w / 2:.1f}" y2="{center_y:.1f}" stroke="#64748b" stroke-width="4" marker-end="url(#arrowHead)" />'
            )

    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
      <defs>
        <filter id="shadow" x="-20%" y="-20%" width="140%" height="160%">
          <feDropShadow dx="0" dy="10" stdDeviation="12" flood-color="#0f172a" flood-opacity="0.18" />
        </filter>
      </defs>
      {defs}
      <rect width="100%" height="100%" fill="#f8fafc" />
      <text x="{margin}" y="54" font-size="28" font-weight="800" fill="#0f172a">{html.escape(title)}</text>
      <text x="{margin}" y="88" font-size="18" fill="#475569">{html.escape(subtitle)}</text>
      {''.join(arrows)}
      {''.join(nodes)}
    </svg>
    """
    path.write_text(svg.strip(), encoding="utf-8")


def render_assignment_report(output_dir: Path) -> Dict[str, Any]:
    dataset_summary = load_json(output_dir / "dataset_summary.json")
    training_results = load_json(output_dir / "training_results.json")
    kb_summary = load_json(output_dir / "kb_graph_summary.json")
    preview_rows = load_rows(output_dir / "data_user500_preview.csv")

    best = training_results["best_model"]
    models = training_results["models"]
    model_rows = [
        [
            name.upper(),
            f'{metrics["validation"]["macro_f1"]:.4f}',
            f'{metrics["test"]["macro_f1"]:.4f}',
            f'{metrics["test"]["accuracy"]:.4f}',
        ]
        for name, metrics in models.items()
    ]

    rows_md = markdown_table(
        ["user_id", "product_id", "action", "timestamp"],
        [[row["user_id"], row["product_id"], row["action"], row["timestamp"]] for row in preview_rows],
    )

    report_lines = [
        "# AISERVICE 02 - TechShop",
        "",
        "## 1. Trang bìa",
        "",
        "| Mục | Nội dung |",
        "| --- | --- |",
        "| Môn học | AI Service |",
        "| Đề tài | AI Service cho TechShop |",
        "| Sinh viên | __________________ |",
        "| Lớp / Nhóm | __________________ |",
        "| Ngày nộp | 20/04/2026 |",
        "",
        "## 2. Mô tả AISERVICE",
        "",
        "AISERVICE là dịch vụ AI của TechShop, phụ trách tracking hành vi người dùng, xây hồ sơ sở thích, gợi ý sản phẩm, truy hồi tri thức cho chat, và đồng bộ dữ liệu hành vi vào Neo4j để phục vụ KB_Graph. Trong bài nộp này, dịch vụ được dùng theo đúng 4 khối yêu cầu của thầy: sinh dữ liệu, train 3 mô hình tuần tự, dựng knowledge graph, và dựng chat/RAG tích hợp e-commerce.",
        "",
        "## 3. Copy 20 dòng data",
        "",
        f"![20 dòng dữ liệu](data_user500_20rows.svg)",
        "",
        rows_md,
        "",
        "## 4. Câu 2a: RNN, LSTM, biLSTM",
        "",
        f"Mục tiêu bài toán là dự đoán action kế tiếp từ chuỗi hành vi trước đó. Dataset có {dataset_summary['users']} user và {dataset_summary['events']} events, được chia theo user để tránh leakage giữa train/validation/test. Metric chính để chọn model_best là macro F1 vì nhãn bị lệch giữa `view`, `click`, và `add_to_cart`.",
        "",
        "### 4.1. Code chính",
        "",
        "```python",
        "class SequenceClassifier:",
        "    def __init__(self, torch, model_type: str, seq_len: int, num_classes: int = 3):",
        "        hidden_size = 48",
        "        emb_dim = 12",
        "        self.embedding = torch.nn.Embedding(4, emb_dim, padding_idx=0)",
        "        if model_type == 'rnn':",
        "            self.sequence = torch.nn.RNN(input_size=emb_dim + 1, hidden_size=hidden_size, batch_first=True)",
        "        elif model_type == 'lstm':",
        "            self.sequence = torch.nn.LSTM(input_size=emb_dim + 1, hidden_size=hidden_size, batch_first=True)",
        "        elif model_type == 'bilstm':",
        "            self.sequence = torch.nn.LSTM(input_size=emb_dim + 1, hidden_size=hidden_size, batch_first=True, bidirectional=True)",
        "```",
        "",
        "```python",
        "def train_models(...):",
        "    for model_name in ['rnn', 'lstm', 'bilstm']:",
        "        model = SequenceClassifier(torch, model_name, seq_len=seq_len)",
        "        optimizer = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=1e-4)",
        "        ...",
        "        if val_metrics['macro_f1'] > best_val_score:",
        "            best_val_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}",
        "    torch.save(best_state, output_dir / 'model_best.pt')",
        "```",
        "",
        "### 4.2. So sánh mô hình",
        "",
        markdown_table(["Model", "Val macro F1", "Test macro F1", "Test accuracy"], model_rows),
        "",
        f"Model được chọn là **{best['name'].upper()}** vì có validation macro F1 cao nhất ({best['macro_f1']:.4f}).",
        "",
        "### 4.3. Ảnh huấn luyện",
        "",
        "![Action distribution](actions_distribution.svg)",
        "![RNN learning curve](rnn_learning_curve.svg)",
        "![LSTM learning curve](lstm_learning_curve.svg)",
        "![biLSTM learning curve](bilstm_learning_curve.svg)",
        "![Model comparison](model_comparison.svg)",
        "![Best model confusion matrix](model_best_confusion_matrix.svg)",
        "",
        "## 5. KB_Graph",
        "",
        f"KB_Graph được sinh từ cùng dataset với {kb_summary['rows']} quan hệ hành vi, {kb_summary['users']} user, {kb_summary['products']} product, và các node Brand/Category/BehaviorProfile để graph nhìn giàu hơn. File `kb_graph_sample_queries.cypher` chứa các truy vấn mẫu để mở trong Neo4j Browser và chụp ảnh.",
        "",
        "### 5.1. Ảnh 20 dòng + graph",
        "",
        "![20 dòng dữ liệu](data_user500_20rows.svg)",
        "![KB graph](kb_graph_preview.svg)",
        "",
        "### 5.2. Ghi chú Neo4j",
        "",
        f"Trạng thái import Neo4j khi sinh artefact: `{kb_summary.get('neo4j_import', 'unknown')}`.",
        "",
        "## 6. Câu 2c và 2d: RAG + e-commerce integration",
        "",
        "### 6.1. RAG chat",
        "",
        "AISERVICE dùng chat endpoint riêng để nhận query, phân loại ý định, truy hồi tri thức từ KB_Graph và knowledge chunks, rồi trả về câu trả lời kèm nguồn và sản phẩm liên quan. Đây là luồng RAG thật, không phải giao diện mặc định của ChatGPT.",
        "",
        "![RAG flow](rag_flow.svg)",
        "",
        "### 6.2. Tích hợp e-commerce",
        "",
        "Khi user search hoặc thêm vào giỏ hàng, frontend gửi event qua gateway sang ai_service để cập nhật graph và profile. Đồng thời giao diện product/cart hiển thị danh sách sản phẩm liên quan thay vì chỉ trả về text.",
        "",
        "![Integration flow](integration_flow.svg)",
        "",
        "### 6.3. Artefact dùng để nộp",
        "",
        "- `data_user500.csv`",
        "- `data_user500_preview.csv`",
        "- `data_user500_20rows.svg`",
        "- `rnn.pt`, `lstm.pt`, `bilstm.pt`, `model_best.pt`",
        "- `actions_distribution.svg`, `model_comparison.svg`, `model_best_confusion_matrix.svg`",
        "- `kb_graph_preview.svg`, `kb_graph_sample_queries.cypher`",
        "- `rag_flow.svg`, `integration_flow.svg`",
        "",
        "## 7. Kết luận",
        "",
        "Bộ artefact này đã phủ đúng cấu trúc đề bài: dữ liệu, 3 mô hình, KB_Graph Neo4j, RAG chat, và tích hợp e-commerce. Từ file Markdown này có thể xuất PDF trực tiếp sau khi điền thông tin bìa.",
    ]

    report_path = output_dir / "aiservice02_report.md"
    report_path.write_text("\n".join(report_lines).strip() + "\n", encoding="utf-8")
    return {
        "report_path": report_path,
        "preview_image": output_dir / "data_user500_20rows.svg",
    }


def build_kb_graph(
    *,
    data_csv: Path,
    product_catalog_json: Path,
    profiles_json: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = load_rows(data_csv)
    catalog_list = load_json(product_catalog_json)
    catalog_by_id = {item["product_id"]: item for item in catalog_list}
    user_profiles = load_json(profiles_json)
    records = build_graph_records(rows, catalog_by_id, user_profiles)

    summary = {
        "rows": len(records),
        "users": len({record.user_id for record in records}),
        "products": len({record.product_id for record in records}),
        "profiles": len({record.behavior_profile for record in records}),
        "brands": len({record.brand_name for record in records if record.brand_name}),
        "categories": len({record.category_name for record in records if record.category_name}),
    }
    write_json(output_dir / "kb_graph_summary.json", summary)
    write_sample_queries(output_dir / "kb_graph_sample_queries.cypher")
    render_graph_preview_svg(
        output_dir / "kb_graph_preview.svg",
        records=records,
        catalog_by_id=catalog_by_id,
        user_profiles=user_profiles,
    )

    try:
        with Neo4jGraphService() as graph_service:
            graph_service.seed_from_rows(records)
        summary["neo4j_import"] = "ok"
    except Exception as exc:  # pragma: no cover - depends on local Neo4j availability
        summary["neo4j_import"] = f"skipped: {exc}"
        logging.getLogger("ai_assignment").warning("Neo4j import skipped: %s", exc)

    write_json(output_dir / "kb_graph_summary.json", summary)
    return summary


def ensure_output_dir(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="TechShop AI assignment pipeline")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Where generated CSVs, plots, and models are written",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--users", type=int, default=500)
    parser.add_argument("--min-events", type=int, default=32)
    parser.add_argument("--max-events", type=int, default=60)
    parser.add_argument(
        "command",
        choices=["generate-data", "train", "build-graph", "all"],
        nargs="?",
        default="all",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger("ai_assignment")
    output_dir = ensure_output_dir(args.output_dir)
    dataset_artifacts: Optional[Dict[str, Any]] = None

    if args.command in {"generate-data", "all"}:
        logger.info("Generating dataset and preview artifacts in %s", output_dir)
        dataset_artifacts = generate_dataset(
            output_dir=output_dir,
            num_users=args.users,
            min_events=args.min_events,
            max_events=args.max_events,
            seed=args.seed,
        )

    if args.command in {"train", "all"}:
        if dataset_artifacts is None:
            data_csv = output_dir / "data_user500.csv"
            if not data_csv.exists():
                dataset_artifacts = generate_dataset(
                    output_dir=output_dir,
                    num_users=args.users,
                    min_events=args.min_events,
                    max_events=args.max_events,
                    seed=args.seed,
                )
            else:
                dataset_artifacts = {
                    "data_csv": data_csv,
                    "preview_csv": output_dir / "data_user500_preview.csv",
                    "product_catalog": output_dir / "product_catalog.json",
                    "profiles": output_dir / "behavior_profiles.json",
                    "summary": output_dir / "dataset_summary.json",
                }
        logger.info("Training RNN/LSTM/biLSTM models")
        train_models(csv_path=dataset_artifacts["data_csv"], output_dir=output_dir, seq_len=12, seed=args.seed)

    if args.command in {"build-graph", "all"}:
        if dataset_artifacts is None:
            data_csv = output_dir / "data_user500.csv"
            product_catalog = output_dir / "product_catalog.json"
            profiles = output_dir / "behavior_profiles.json"
            if not data_csv.exists() or not product_catalog.exists() or not profiles.exists():
                dataset_artifacts = generate_dataset(
                    output_dir=output_dir,
                    num_users=args.users,
                    min_events=args.min_events,
                    max_events=args.max_events,
                    seed=args.seed,
                )
            else:
                dataset_artifacts = {
                    "data_csv": data_csv,
                    "preview_csv": output_dir / "data_user500_preview.csv",
                    "product_catalog": product_catalog,
                    "profiles": profiles,
                    "summary": output_dir / "dataset_summary.json",
                }
        logger.info("Building KB_Graph artifacts")
        build_kb_graph(
            data_csv=dataset_artifacts["data_csv"],
            product_catalog_json=dataset_artifacts["product_catalog"],
            profiles_json=dataset_artifacts["profiles"],
            output_dir=output_dir,
        )

    if args.command == "all":
        logger.info("Rendering assignment report")
        render_rows_table_svg(output_dir / "data_user500_20rows.svg", load_rows(output_dir / "data_user500_preview.csv"), "20 dòng dữ liệu mẫu")
        render_flow_diagram_svg(
            output_dir / "rag_flow.svg",
            title="RAG chat flow",
            subtitle="Chat UI truy hồi knowledge chunks và graph facts trước khi sinh câu trả lời",
            steps=[
                ("User", "Ask a shopping question", "#0ea5e9"),
                ("Chat UI", "Next.js page", "#2563eb"),
                ("Gateway", "Nginx proxy", "#475569"),
                ("RAG Engine", "Intent + retrieval", "#7c3aed"),
                ("KB_Graph", "Neo4j + docs", "#16a34a"),
                ("Answer", "Sources + products", "#f97316"),
            ],
        )
        render_flow_diagram_svg(
            output_dir / "integration_flow.svg",
            title="E-commerce integration flow",
            subtitle="Search và add-to-cart cùng đẩy event sang AI service để cập nhật graph và danh sách gợi ý",
            steps=[
                ("Search / Cart", "User action", "#0f766e"),
                ("Frontend", "Product / cart UI", "#0ea5e9"),
                ("Gateway", "Route events", "#475569"),
                ("AI tracking", "Event ingest", "#8b5cf6"),
                ("Neo4j graph", "Sync behavior", "#16a34a"),
                ("Product list", "Related items", "#f97316"),
            ],
        )
        render_assignment_report(output_dir)


if __name__ == "__main__":
    main()
