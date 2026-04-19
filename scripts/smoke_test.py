"""
Quick smoke test for the TechShop end-to-end demo flow.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict
from urllib import error, parse, request


DEFAULT_BASE_URL = "http://localhost:8080"


def api_call(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    data: Dict[str, Any] | None = None,
    headers: Dict[str, str] | None = None,
) -> Any:
    body = None
    merged_headers = {"Content-Type": "application/json"}
    if headers:
        merged_headers.update(headers)
    if data is not None:
        body = json.dumps(data).encode("utf-8")
    req = request.Request(f"{base_url}{path}", data=body, headers=merged_headers, method=method)
    try:
        with request.urlopen(req, timeout=30) as resp:
            payload = resp.read().decode("utf-8")
            parsed_payload = json.loads(payload)
            return parsed_payload.get("data", parsed_payload)
    except error.HTTPError as exc:
        content = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"{method} {path} failed: {exc.code} {content}") from exc


def login(base_url: str, email: str, password: str) -> Dict[str, Any]:
    return api_call(
        base_url,
        "/user/api/v1/auth/login/",
        method="POST",
        data={"email": email, "password": password},
    )


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def wait_for_order(base_url: str, order_id: str, headers: Dict[str, str], predicate, timeout: int = 45) -> Dict[str, Any]:
    deadline = time.time() + timeout
    last_order: Dict[str, Any] | None = None
    while time.time() < deadline:
        last_order = api_call(base_url, f"/order/api/v1/orders/{order_id}/", headers=headers)
        if predicate(last_order):
            return last_order
        time.sleep(2)
    raise RuntimeError(f"Order {order_id} did not reach expected state. Last payload: {last_order}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test TechShop demo flow")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")

    print("1. Login customer")
    customer_auth = login(base_url, "john@example.com", "Demo@123456")
    customer = customer_auth["user"]
    customer_headers = {
        "Authorization": f"Bearer {customer_auth['access']}",
        "X-User-ID": customer["id"],
        "X-User-Role": customer.get("role", "customer"),
    }

    print("2. List products")
    products = api_call(base_url, "/product/api/v1/catalog/products/?page_size=5", headers=customer_headers)
    assert_true(bool(products.get("results")), "No products returned from catalog")
    first_product = products["results"][0]

    print("3. Search products")
    search_results = api_call(base_url, "/product/api/v1/catalog/products/?search=laptop&page_size=5", headers=customer_headers)
    assert_true(search_results.get("count", 0) >= 1, "Product search returned no results")

    print("4. Add to cart")
    cart = api_call(
        base_url,
        "/cart/api/v1/cart/items/",
        method="POST",
        data={"product_id": first_product["id"], "quantity": 1},
        headers=customer_headers,
    )
    assert_true(bool(cart.get("items")), "Cart is empty after add-to-cart")

    print("5. Create order from cart")
    order = api_call(
        base_url,
        "/order/api/v1/orders/from-cart/",
        method="POST",
        data={
            "cart_id": cart["id"],
            "shipping_address": {
                "receiver_name": "John Doe",
                "receiver_phone": "+84912345680",
                "line1": "123 Tran Hung Dao",
                "district": "District 1",
                "city": "Ho Chi Minh",
                "country": "Vietnam",
            },
            "notes": "Smoke test order",
        },
        headers=customer_headers,
    )
    order_id = order["id"]
    assert_true(bool(order.get("payment_reference")), "Order missing payment reference")

    print("6. Mock payment success")
    api_call(
        base_url,
        "/payment/api/v1/webhooks/mock/",
        method="POST",
        data={"payment_reference": order["payment_reference"], "status": "completed"},
    )
    paid_order = wait_for_order(
        base_url,
        order_id,
        customer_headers,
        lambda payload: payload.get("payment_status") == "paid" and bool(payload.get("shipment_reference")),
    )

    print("7. Login staff and update shipping")
    staff_auth = login(base_url, "staff@techshop.com", "Demo@123456")
    staff_headers = {
        "Authorization": f"Bearer {staff_auth['access']}",
        "X-User-ID": staff_auth["user"]["id"],
        "X-User-Role": staff_auth["user"].get("role", "staff"),
        "X-Admin": "true",
    }
    api_call(
        base_url,
        f"/shipping/api/v1/operations/shipments/order/{order_id}/status/",
        method="PATCH",
        data={"status": "in_transit"},
        headers=staff_headers,
    )
    api_call(
        base_url,
        f"/shipping/api/v1/operations/shipments/order/{order_id}/status/",
        method="PATCH",
        data={"status": "delivered"},
        headers=staff_headers,
    )

    print("8. Recommendations and behavior analytics")
    recommendations = api_call(
        base_url,
        f"/ai/api/v1/ai/recommendations/{customer['id']}/?limit=5",
        headers=customer_headers,
    )
    assert_true(bool(recommendations.get("products")), "Recommendations returned no products")
    behavior_summary = api_call(base_url, "/ai/api/v1/ai/behavior/summary/", headers=customer_headers)
    assert_true(behavior_summary.get("total_events", 0) >= 1, "Behavior summary is empty")

    print("9. Rebuild KG, train LSTM, rebuild RAG")
    api_call(base_url, "/ai/api/v1/ai/kg/rebuild/", method="POST", data={"clear_graph": True}, headers=staff_headers)
    api_call(
        base_url,
        "/ai/api/v1/ai/lstm/train/",
        method="POST",
        data={"dataset": "/app/data/data_100users.csv", "epochs": 4, "sequence_length": 5, "batch_size": 16},
        headers=staff_headers,
    )
    api_call(base_url, "/ai/api/v1/ai/rag/rebuild/", method="POST", data={"replace": True}, headers=staff_headers)

    print("10. Chat RAG")
    session = api_call(base_url, "/ai/api/v1/ai/chat/sessions/", method="POST", data={"user_id": customer["id"]}, headers=customer_headers)
    answer = api_call(
        base_url,
        "/ai/api/v1/ai/chat/",
        method="POST",
        data={"session_id": session["id"], "user_id": customer["id"], "query": "Chinh sach giao hang va goi y mot laptop cho cong viec van phong"},
        headers=customer_headers,
    )
    assert_true(bool(answer.get("answer")), "Chat answer is empty")

    print("Smoke test completed successfully")
    print(json.dumps(
        {
            "order_id": order_id,
            "shipment_reference": paid_order.get("shipment_reference"),
            "recommended_products": len(recommendations.get("products", [])),
            "behavior_events": behavior_summary.get("total_events", 0),
        },
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover
        print(f"Smoke test failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
