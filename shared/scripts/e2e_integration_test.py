#!/usr/bin/env python3
"""
End-to-End Integration Test Suite for TechShop Microservices

Tests complete user journeys across all services to ensure system integration.
Run with: python e2e_integration_test.py [--verbose] [--cleanup]
"""

import os
import sys
import json
import time
import uuid
import requests
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, Optional
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Service URLs
SERVICES = {
    'user': os.getenv('USER_SERVICE_URL', 'http://localhost:8001'),
    'product': os.getenv('PRODUCT_SERVICE_URL', 'http://localhost:8002'),
    'inventory': os.getenv('INVENTORY_SERVICE_URL', 'http://localhost:8007'),
    'cart': os.getenv('CART_SERVICE_URL', 'http://localhost:8003'),
    'order': os.getenv('ORDER_SERVICE_URL', 'http://localhost:8004'),
    'payment': os.getenv('PAYMENT_SERVICE_URL', 'http://localhost:8005'),
    'shipping': os.getenv('SHIPPING_SERVICE_URL', 'http://localhost:8006'),
    'ai': os.getenv('AI_SERVICE_URL', 'http://localhost:8008'),
}

INTERNAL_KEY = os.getenv('INTERNAL_SERVICE_KEY', 'internal-secret-key')
TIMEOUT = 10


class E2ETestRunner:
    """Orchestrates end-to-end integration tests."""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.test_results = []
        self.created_resources = {
            'users': [],
            'products': [],
            'carts': [],
            'orders': [],
            'payments': [],
        }
    
    def log(self, msg: str, level='INFO'):
        """Log message."""
        getattr(logger, level.lower())(msg)
    
    def log_section(self, title: str):
        """Log section header."""
        self.log(f"\n{'='*60}", 'info')
        self.log(f"  {title}", 'info')
        self.log(f"{'='*60}", 'info')
    
    def make_request(self, method: str, service: str, path: str, 
                     data: Optional[Dict] = None, auth_token: Optional[str] = None,
                     internal=False) -> tuple[bool, Any]:
        """Make HTTP request to service."""
        url = f"{SERVICES[service]}{path}"
        headers = {"Content-Type": "application/json"}
        
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        if internal:
            headers["X-Internal-Service-Key"] = INTERNAL_KEY
        
        try:
            if method == "GET":
                resp = requests.get(url, headers=headers, timeout=TIMEOUT)
            elif method == "POST":
                resp = requests.post(url, json=data, headers=headers, timeout=TIMEOUT)
            elif method == "PATCH":
                resp = requests.patch(url, json=data, headers=headers, timeout=TIMEOUT)
            else:
                raise ValueError(f"Unsupported method {method}")
            
            if resp.status_code in [200, 201]:
                return True, resp.json()
            else:
                self.log(f"  ERROR {resp.status_code}: {resp.text}", 'error')
                return False, resp.json() if resp.text else {}
        except Exception as e:
            self.log(f"  REQUEST FAILED: {str(e)}", 'error')
            return False, {}
    
    def assert_success(self, success: bool, test_name: str) -> bool:
        """Assert test succeeded."""
        if success:
            self.log(f"  ✅ {test_name}", 'info')
            self.test_results.append((test_name, True))
            return True
        else:
            self.log(f"  ❌ {test_name}", 'error')
            self.test_results.append((test_name, False))
            return False
    
    # ===== FLOW 1: User Registration & Authentication =====
    
    def test_user_auth_flow(self) -> Optional[str]:
        """Flow 1: Register user and login."""
        self.log_section("FLOW 1: User Auth & Registration")
        
        email = f"testuser_{uuid.uuid4().hex[:8]}@example.com"
        self.log(f"Creating test user: {email}")
        
        success, data = self.make_request(
            "POST", "user", "/api/v1/auth/register/",
            {
                "email": email,
                "full_name": "Test User",
                "password": "TestPass123!",
                "confirm_password": "TestPass123!",
                "phone_number": "+84123456789"
            }
        )
        self.assert_success(success, "User registration")
        
        if not success:
            return None
        user_id = data.get("data", {}).get("id")
        self.created_resources['users'].append(user_id)
        
        # Login
        success, logindata = self.make_request(
            "POST", "user", "/api/v1/auth/login/",
            {"email": email, "password": "TestPass123!"}
        )
        self.assert_success(success, "User login")
        
        if not success:
            return None
        
        token = logindata.get("data", {}).get("access")
        self.log(f"  User ID: {user_id}", 'info')
        self.log(f"  Token obtained (length: {len(token) if token else 0})", 'info')
        return token
    
    # ===== FLOW 2: Product Catalog Browsing & Search =====
    
    def test_product_catalog_flow(self) -> Optional[Dict]:
        """Flow 2: Browse products and get details."""
        self.log_section("FLOW 2: Product Catalog Browsing")
        
        # List products
        success, data = self.make_request("GET", "product", "/api/v1/catalog/products/")
        self.assert_success(success, "List products")
        
        if not success or not data.get("data", {}).get("results"):
            self.log("  No products found. Run seed first!", 'warning')
            return None
        
        product = data["data"]["results"][0]
        product_id = product.get("id")
        self.created_resources['products'].append(product_id)
        self.log(f"  Found product: {product.get('name')} (${product.get('base_price')})", 'info')
        
        # Get product details
        success, detail_data = self.make_request(
            "GET", "product", f"/api/v1/catalog/products/{product_id}/"
        )
        self.assert_success(success, "Get product detail")
        
        if success:
            self.log(f"  Variants: {len(detail_data.get('data', {}).get('variants', []))}", 'info')
        
        return product
    
    # ===== FLOW 3: Add to Cart =====
    
    def test_add_to_cart_flow(self, token: str, product: Dict) -> Optional[str]:
        """Flow 3: Add product to cart."""
        self.log_section("FLOW 3: Add to Cart")
        
        if not token or not product:
            self.log("  Skipping: Missing prerequisites", 'warning')
            return None
        
        product_id = product.get("id")
        
        # Add to cart
        success, data = self.make_request(
            "POST", "cart", "/api/v1/cart/items/",
            {
                "product_id": product_id,
                "quantity": 2,
            },
            auth_token=token
        )
        self.assert_success(success, "Add item to cart")
        
        if not success:
            return None
        
        # Get updated cart
        success, cart_data = self.make_request(
            "GET", "cart", "/api/v1/cart/",
            auth_token=token
        )
        self.assert_success(success, "Get updated cart")
        
        if success:
            cart = cart_data.get("data", {})
            cart_id = cart.get("id")
            self.log(f"  Cart ID: {cart_id}", 'info')
            self.log(f"  Items in cart: {cart.get('item_count')}", 'info')
            self.log(f"  Subtotal: {cart.get('subtotal_amount')}", 'info')
            self.created_resources['carts'].append(cart_id)
            return cart_id
        
        return None
    
    # ===== FLOW 4: Checkout Preview =====
    
    def test_checkout_preview_flow(self, token: str) -> Optional[Dict]:
        """Flow 4: Get checkout preview before creating order."""
        self.log_section("FLOW 4: Checkout Preview")
        
        if not token:
            self.log("  Skipping: Missing auth token", 'warning')
            return None
        
        success, data = self.make_request(
            "POST", "cart", "/api/v1/cart/checkout-preview/",
            {},
            auth_token=token
        )
        self.assert_success(success, "Get checkout preview")
        
        if success:
            preview = data.get("data", {})
            self.log(f"  Valid: {preview.get('is_valid')}", 'info')
            self.log(f"  Issues: {len(preview.get('issues', []))}", 'info')
            if preview.get('checkout_payload'):
                payload = preview['checkout_payload']
                self.log(f"  Checkout subtotal: {payload.get('subtotal_amount')}", 'info')
            return preview
        
        return None
    
    # ===== FLOW 5: Create Order & Track Payment =====
    
    def test_order_creation_flow(self, token: str, user_id: str) -> Optional[str]:
        """Flow 5: Create order and track payment."""
        self.log_section("FLOW 5: Create Order & Payment")
        
        if not token:
            self.log("  Skipping: Missing auth token", 'warning')
            return None
        
        # Get active cart
        success, cart_data = self.make_request(
            "GET", "cart", "/api/v1/cart/",
            auth_token=token
        )
        
        if not success or not cart_data.get("data", {}).get("item_count"):
            self.log("  Skipping: Cart is empty", 'warning')
            return None
        
        cart = cart_data.get("data", {})
        cart_id = cart.get("id")
        
        # Create order from cart
        success, data = self.make_request(
            "POST", "order", "/api/v1/orders/",
            {
                "cart_id": cart_id,
                "shipping_address": {
                    "receiver_name": "Test Customer",
                    "receiver_phone": "+84123456789",
                    "line1": "123 Test Street",
                    "district": "District 1",
                    "city": "Ho Chi Minh",
                    "country": "Vietnam",
                }
            },
            auth_token=token
        )
        self.assert_success(success, "Create order")
        
        if not success:
            return None
        
        order = data.get("data", {})
        order_id = order.get("id")
        order_number = order.get("order_number")
        payment_id = order.get("payment_id")
        
        self.created_resources['orders'].append(order_id)
        self.log(f"  Order ID: {order_id}", 'info')
        self.log(f"  Order Number: {order_number}", 'info')
        self.log(f"  Payment ID: {payment_id}", 'info')
        self.log(f"  Status: {order.get('status')}", 'info')
        
        # Check payment status
        if payment_id:
            success, payment_data = self.make_request(
                "GET", "payment", f"/api/v1/payments/{payment_id}/",
                auth_token=token
            )
            self.assert_success(success, "Get payment status")
            
            if success:
                payment = payment_data.get("data", {})
                self.log(f"  Payment status: {payment.get('status')}", 'info')
                self.log(f"  Payment reference: {payment.get('payment_reference')}", 'info')
                self.created_resources['payments'].append(payment_id)
        
        return order_id
    
    # ===== FLOW 6: Mock Payment Success =====
    
    def test_mock_payment_success_flow(self, order_id: str, payment_id: str) -> bool:
        """Flow 6: Trigger mock payment success."""
        self.log_section("FLOW 6: Mock Payment Success")
        
        if not order_id or not payment_id:
            self.log("  Skipping: Missing order or payment", 'warning')
            return False
        
        # Trigger mock payment success
        success, data = self.make_request(
            "POST", "payment", f"/api/v1/webhooks/mock/",
            {
                "payment_reference": payment_id,
                "provider_payment_id": f"mock_{uuid.uuid4().hex[:8]}",
                "status": "completed",
                "amount": 1000.00,
            }
        )
        self.assert_success(success, "Trigger mock payment success")
        
        if not success:
            return False
        
        # Wait a bit for async processing
        time.sleep(1)
        
        # Check order status updated
        success, order_data = self.make_request(
            "GET", "order", f"/api/v1/orders/{order_id}/",
            internal=True
        )
        self.assert_success(success, "Get updated order after payment")
        
        if success:
            order = order_data.get("data", {})
            self.log(f"  Order status: {order.get('status')}", 'info')
            self.log(f"  Payment status: {order.get('payment_status')}", 'info')
        
        return True
    
    # ===== FLOW 7: Shipment Tracking =====
    
    def test_shipment_flow(self, order_id: str) -> bool:
        """Flow 7: Check shipment and mock delivery."""
        self.log_section("FLOW 7: Shipment & Tracking")
        
        if not order_id:
            self.log("  Skipping: Missing order", 'warning')
            return False
        
        # Get order to find shipment
        success, order_data = self.make_request(
            "GET", "order", f"/api/v1/orders/{order_id}/",
            internal=True
        )
        self.assert_success(success, "Get order with shipment info")
        
        if not success:
            return False
        
        order = order_data.get("data", {})
        shipment_id = order.get("shipment_id")
        
        if not shipment_id:
            self.log("  No shipment created yet", 'warning')
            return False
        
        self.log(f"  Shipment ID: {shipment_id}", 'info')
        
        # Get shipment details
        success, shipment_data = self.make_request(
            "GET", "shipping", f"/api/v1/shipments/{shipment_id}/",
            internal=True
        )
        self.assert_success(success, "Get shipment details")
        
        if success:
            shipment = shipment_data.get("data", {})
            self.log(f"  Status: {shipment.get('status')}", 'info')
            self.log(f"  Tracking #: {shipment.get('tracking_number')}", 'info')
        
        return True
    
    # ===== FLOW 8: AI Recommendations =====
    
    def test_ai_recommendation_flow(self, user_id: str, token: str, product: Dict) -> bool:
        """Flow 8: Check AI recommendations and RAG chat after order."""
        self.log_section("FLOW 8: AI Recommendations & Chat")
        
        if not user_id or not token:
            self.log("  Skipping: Missing user or token", 'warning')
            return False
        
        # Get user preferences
        success, pref_data = self.make_request(
            "GET", "ai", f"/api/v1/ai/users/{user_id}/preferences/",
            auth_token=token
        )
        self.assert_success(success, "Get user preferences")
        
        if success:
            prefs = pref_data.get("data", {})
            self.log(f"  Preferred brands: {prefs.get('top_brands', [])}", 'info')
            self.log(f"  Top category: {prefs.get('top_category', 'N/A')}", 'info')
            self.log(f"  Purchase intent: {prefs.get('purchase_intent_score', 0)}", 'info')
        
        # Get recommendations
        success, rec_data = self.make_request(
            "POST", "ai", "/api/v1/ai/recommendations/",
            {
                "user_id": user_id,
                "products": [
                    {
                        "id": product.get("id"),
                        "name": product.get("name"),
                        "brand": product.get("brand_name") or "",
                        "category": product.get("category_name") or "",
                        "price": product.get("base_price"),
                        "thumbnail_url": product.get("thumbnail_url"),
                    }
                ],
            },
            auth_token=token
        )
        self.assert_success(success, "Get AI recommendations")
        
        if success:
            recs = rec_data.get("data", {})
            products = recs.get("products", [])[:3]
            self.log(f"  Top recommendations: {len(recs.get('products', []))}", 'info')
            for i, prod in enumerate(products, 1):
                self.log(f"    {i}. {prod.get('name')} (score: {prod.get('score')})", 'info')

        success, chat_data = self.make_request(
            "POST", "ai", "/api/v1/ai/chat/ask/",
            {
                "query": "Chinh sach doi tra nhu the nao?",
                "user_id": user_id,
            },
            auth_token=token,
        )
        self.assert_success(success, "Ask AI chat")
        if success:
            answer = chat_data.get("data", {})
            self.log(f"  Chat sources: {len(answer.get('sources', []))}", 'info')
            self.log(f"  Chat mode: {answer.get('mode')}", 'info')

        return True
    
    def run_all_flows(self):
        """Execute all integration test flows."""
        self.log("\n" + "="*60)
        self.log("  TECHSHOP E2E INTEGRATION TEST SUITE")
        self.log("="*60)
        self.log(f"Timestamp: {datetime.now().isoformat()}")
        self.log(f"Services: {', '.join(SERVICES.keys())}")
        
        try:
            # FLOW 1: Auth
            token = self.test_user_auth_flow()
            if not token:
                self.log("\nStopping: User auth failed", 'error')
                return False
            
            # Extract user_id from internal call (for demo, use a UUID)
            user_id = str(uuid.uuid4())
            
            # FLOW 2: Product Catalog
            product = self.test_product_catalog_flow()
            
            # FLOW 3: Add to Cart
            cart_id = self.test_add_to_cart_flow(token, product)
            
            # FLOW 4: Checkout Preview
            checkout_preview = self.test_checkout_preview_flow(token)
            
            # FLOW 5: Create Order
            order_id = self.test_order_creation_flow(token, user_id)
            
            # FLOW 6: Mock Payment
            if order_id:
                # Get payment_id from order first
                success, order_data = self.make_request(
                    "GET", "order", f"/api/v1/orders/{order_id}/",
                    internal=True
                )
                if success:
                    payment_id = order_data.get("data", {}).get("payment_id")
                    self.test_mock_payment_success_flow(order_id, payment_id)
            
            # FLOW 7: Shipment
            if order_id:
                self.test_shipment_flow(order_id)
            
            # FLOW 8: AI
            self.test_ai_recommendation_flow(user_id, token, product)
            
        except Exception as e:
            self.log(f"\nTest execution error: {str(e)}", 'error')
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            self._print_summary()
    
    def _print_summary(self):
        """Print test results summary."""
        self.log_section("TEST SUMMARY")
        
        passed = sum(1 for _, result in self.test_results if result)
        total = len(self.test_results)
        
        for test_name, result in self.test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"  {status}: {test_name}", 'info')
        
        self.log(f"\nResults: {passed}/{total} tests passed ({int(passed*100/total if total else 0)}%)", 'info')
        self.log(f"Created resources: {json.dumps(self.created_resources, indent=2)}", 'info')
        
        return passed == total


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='E2E Integration Test Suite')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--cleanup', action='store_true', help='Cleanup created resources')
    
    args = parser.parse_args()
    
    runner = E2ETestRunner(verbose=args.verbose)
    runner.run_all_flows()
    
    # Cleanup if requested
    if args.cleanup:
        logger.info("Cleanup requested but not yet implemented")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
