import http from "node:http";
import { URL } from "node:url";

const port = Number(process.env.PORT ?? "8081");

const products = [
  {
    id: "prod-iphone-15",
    name: "iPhone 15",
    slug: "iphone-15",
    short_description: "Điện thoại flagship cho storefront demo.",
    brand_name: "Apple",
    category_name: "Điện thoại",
    base_price: 19990000,
    currency: "VND",
    thumbnail_url: "https://images.unsplash.com/photo-1695048133142-1a2049d5e7bd?auto=format&fit=crop&w=900&q=80",
    status: "active",
  },
  {
    id: "prod-galaxy-s24",
    name: "Galaxy S24",
    slug: "galaxy-s24",
    short_description: "Sản phẩm demo thứ hai dùng trong kiểm thử E2E.",
    brand_name: "Samsung",
    category_name: "Điện thoại",
    base_price: 18990000,
    currency: "VND",
    thumbnail_url: "https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?auto=format&fit=crop&w=900&q=80",
    status: "active",
  },
];

const categories = [
  { id: "cat-phone", name: "Điện thoại", slug: "dien-thoai" },
  { id: "cat-laptop", name: "Laptop", slug: "laptop" },
];

const brands = [
  { id: "brand-apple", name: "Apple", slug: "apple" },
  { id: "brand-samsung", name: "Samsung", slug: "samsung" },
];

const profile = {
  id: "user-123",
  email: "john@example.com",
  full_name: "John Doe",
  role: "customer",
};

const addresses = [
  {
    id: "addr-1",
    receiver_name: "John Doe",
    phone_number: "+84912345680",
    line1: "123 Demo Street",
    district: "District 1",
    city: "Ho Chi Minh City",
    country: "Vietnam",
    is_default: true,
  },
];

const cartSummary = {
  item_count: 2,
  total_quantity: 2,
  subtotal_amount: 38980000,
  currency: "VND",
};

function sendJson(res, statusCode, data) {
  const body = JSON.stringify({ success: true, data });
  res.writeHead(statusCode, {
    "Content-Type": "application/json",
    "Content-Length": Buffer.byteLength(body),
  });
  res.end(body);
}

function sendError(res, statusCode, message) {
  const body = JSON.stringify({ success: false, message });
  res.writeHead(statusCode, {
    "Content-Type": "application/json",
    "Content-Length": Buffer.byteLength(body),
  });
  res.end(body);
}

function readBody(req) {
  return new Promise((resolve) => {
    const chunks = [];
    req.on("data", (chunk) => chunks.push(chunk));
    req.on("end", () => {
      const text = Buffer.concat(chunks).toString("utf8");
      if (!text) {
        resolve(null);
        return;
      }
      try {
        resolve(JSON.parse(text));
      } catch {
        resolve(text);
      }
    });
  });
}

const server = http.createServer(async (req, res) => {
  const requestUrl = new URL(req.url ?? "/", "http://127.0.0.1");
  const { pathname } = requestUrl;

  if (req.method === "GET" && pathname === "/health") {
    sendJson(res, 200, { ok: true });
    return;
  }

  if (req.method === "GET" && pathname === "/product/api/v1/catalog/products/") {
    sendJson(res, 200, { count: products.length, next: null, previous: null, results: products });
    return;
  }

  if (req.method === "GET" && pathname === "/product/api/v1/catalog/categories/") {
    sendJson(res, 200, { count: categories.length, next: null, previous: null, results: categories });
    return;
  }

  if (req.method === "GET" && pathname === "/product/api/v1/catalog/brands/") {
    sendJson(res, 200, { count: brands.length, next: null, previous: null, results: brands });
    return;
  }

  if (req.method === "GET" && pathname === "/cart/api/v1/cart/summary/") {
    sendJson(res, 200, cartSummary);
    return;
  }

  if (req.method === "GET" && pathname === "/user/api/v1/auth/me/") {
    sendJson(res, 200, profile);
    return;
  }

  if (req.method === "GET" && pathname === "/user/api/v1/profile/addresses/") {
    sendJson(res, 200, addresses);
    return;
  }

  if (req.method === "POST" && pathname === "/ai/api/v1/ai/recommendations/") {
    await readBody(req);
    sendJson(res, 200, {
      products: products.map((product, index) => ({
        product_id: product.id,
        product_name: product.name,
        brand: product.brand_name,
        price: product.base_price,
        score: 100 - index * 10,
        reason_codes: index === 0 ? ["preferred_brand"] : ["popular"],
        thumbnail_url: product.thumbnail_url,
      })),
    });
    return;
  }

  if (req.method === "POST" && pathname === "/ai/api/v1/ai/events/track/") {
    await readBody(req);
    sendJson(res, 201, { event_id: "evt-1" });
    return;
  }

  sendError(res, 404, `Unhandled mock backend route: ${req.method} ${pathname}`);
});

server.listen(port, "127.0.0.1", () => {
  // Keep the process alive for Playwright's webServer lifecycle.
  console.log(`mock-backend listening on http://127.0.0.1:${port}`);
});
