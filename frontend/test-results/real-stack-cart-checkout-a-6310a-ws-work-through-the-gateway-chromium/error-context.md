# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: real-stack.spec.ts >> cart, checkout, and order detail flows work through the gateway
- Location: tests/e2e/real-stack.spec.ts:77:5

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('heading', { name: 'Giỏ hàng của bạn.' })
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for getByRole('heading', { name: 'Giỏ hàng của bạn.' })

```

# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - generic [ref=e2]:
    - banner [ref=e3]:
      - generic [ref=e4]:
        - link "TechShop Digital Atelier" [ref=e5] [cursor=pointer]:
          - /url: /
          - img [ref=e7]
          - generic [ref=e9]:
            - generic [ref=e10]: TechShop
            - generic [ref=e11]: Digital Atelier
        - navigation [ref=e12]:
          - link "Sản phẩm" [ref=e13] [cursor=pointer]:
            - /url: /products
          - link "Đơn hàng" [ref=e14] [cursor=pointer]:
            - /url: /orders
          - link "AI Assistant" [ref=e15] [cursor=pointer]:
            - /url: /chat
        - generic [ref=e16]:
          - link "Cart" [ref=e17] [cursor=pointer]:
            - /url: /cart
            - img [ref=e19]
          - generic [ref=e22]:
            - link "John Doe" [ref=e23] [cursor=pointer]:
              - /url: /profile
              - img [ref=e24]
              - generic [ref=e28]: John Doe
            - button [ref=e29] [cursor=pointer]:
              - img [ref=e30]
    - main [ref=e33]:
      - generic [ref=e34]:
        - img [ref=e36]
        - heading "Giỏ hàng của bạn đang trống" [level=2] [ref=e39]
        - paragraph [ref=e40]: Đừng bỏ lỡ các ưu đãi hấp dẫn. Khám phá những sản phẩm công nghệ mới nhất ngay bây giờ!
        - link "Tiếp tục mua hàng" [ref=e41] [cursor=pointer]:
          - /url: /
    - contentinfo [ref=e42]:
      - generic [ref=e43]:
        - generic [ref=e44]:
          - generic [ref=e45]:
            - paragraph [ref=e46]: TechShop Experience Platform
            - paragraph [ref=e47]: Microservices Commerce Frontend
          - generic [ref=e48]:
            - generic [ref=e49]: Realtime Inventory
            - generic [ref=e50]: AI Assisted
            - generic [ref=e51]: Secure Checkout
        - paragraph [ref=e52]: Designed for interactive demo and production-ready service integration.
    - button "Hỏi AI" [ref=e54] [cursor=pointer]:
      - img [ref=e55]
      - text: Hỏi AI
  - alert [ref=e57]
```

# Test source

```ts
  1   | import { expect, test } from "@playwright/test";
  2   | import {
  3   |   loginThroughUi,
  4   |   registerThroughUi,
  5   |   submitAddressForm,
  6   |   uniqueEmail,
  7   |   withNoServerErrors,
  8   | } from "./helpers";
  9   | 
  10  | test.describe.configure({ mode: "serial" });
  11  | 
  12  | const CUSTOMER_EMAIL = "john@example.com";
  13  | const ADMIN_EMAIL = "admin@example.com";
  14  | const DEMO_PASSWORD = "Demo@123456";
  15  | 
  16  | test("anonymous users are redirected to login from protected routes", async ({ page }) =>
  17  |   withNoServerErrors(page, async () => {
  18  |     await page.goto("/checkout");
  19  |     await expect(page).toHaveURL(/\/login/);
  20  |     await expect(page.getByRole("heading", { name: "Đăng nhập tài khoản" })).toBeVisible();
  21  |   }));
  22  | 
  23  | test("registration and login work with the real auth service", async ({ page }) =>
  24  |   withNoServerErrors(page, async () => {
  25  |     const email = uniqueEmail("playwright-customer");
  26  | 
  27  |     await registerThroughUi(page, {
  28  |       full_name: "Playwright Customer",
  29  |       email,
  30  |       password: DEMO_PASSWORD,
  31  |       phone_number: "+84900000001",
  32  |     });
  33  | 
  34  |     await page.goto("/profile");
  35  |     await expect(page.getByRole("heading", { name: "Hồ sơ tài khoản" })).toBeVisible();
  36  |     await expect(page.getByRole("button", { name: "Đăng xuất" })).toBeVisible();
  37  | 
  38  |     await page.getByRole("button", { name: "Đăng xuất" }).click();
  39  |     await expect(page).toHaveURL(/\/login/);
  40  |     await expect(page.getByRole("heading", { name: "Đăng nhập tài khoản" })).toBeVisible();
  41  | 
  42  |     await loginThroughUi(page, CUSTOMER_EMAIL);
  43  |     await page.goto("/profile");
  44  |     await expect(page.getByText("Họ tên: John Doe", { exact: true })).toBeVisible();
  45  |   }));
  46  | 
  47  | test("home and catalog surfaces render seeded products and recommendations", async ({ page }) =>
  48  |   withNoServerErrors(page, async () => {
  49  |     await loginThroughUi(page, CUSTOMER_EMAIL);
  50  | 
  51  |     await page.goto("/");
  52  |     await expect(page.getByRole("heading", { name: "Mua sắm công nghệ theo cách hoàn toàn mới." })).toBeVisible();
  53  |     await expect(page.getByRole("heading", { name: "Sản phẩm nổi bật" })).toBeVisible();
  54  |     await expect(page.getByRole("heading", { name: "iPhone 15" }).first()).toBeVisible();
  55  |     await expect(page.getByRole("heading", { name: "Gợi ý AI cho bạn" })).toBeVisible();
  56  | 
  57  |     await page.goto("/products");
  58  |     await expect(page.getByRole("heading", { name: "Danh mục sản phẩm" })).toBeVisible();
  59  |     await page.getByPlaceholder("Tìm laptop, điện thoại, thương hiệu...").fill("Galaxy");
  60  |     await page.getByRole("button", { name: "Tìm" }).click();
  61  |     await expect(page.getByRole("heading", { name: "Galaxy S24" }).first()).toBeVisible();
  62  | 
  63  |     await page.locator("aside").getByRole("combobox").first().selectOption({ label: "Dien thoai" });
  64  |     await page.locator("aside").getByRole("combobox").nth(1).selectOption({ label: "Samsung" });
  65  |     await page.getByText("Sắp xếp").locator("..").getByRole("combobox").selectOption("-base_price");
  66  |     await expect(page.getByRole("heading", { name: "Galaxy S24" }).first()).toBeVisible();
  67  | 
  68  |     await Promise.all([
  69  |       page.waitForURL(/\/products\/[^/]+$/),
  70  |       page.getByRole("link", { name: "Galaxy S24", exact: true }).click(),
  71  |     ]);
  72  |     await expect(page.getByRole("heading", { name: "Galaxy S24", exact: true })).toBeVisible({ timeout: 10_000 });
  73  |     await expect(page.getByText("Galaxy S24 - demo product", { exact: true })).toBeVisible({ timeout: 10_000 });
  74  |     await expect(page.getByRole("heading", { name: "Sản phẩm liên quan" })).toBeVisible({ timeout: 10000 });
  75  |   }));
  76  | 
  77  | test("cart, checkout, and order detail flows work through the gateway", async ({ page }) =>
  78  |   withNoServerErrors(page, async () => {
  79  |     await loginThroughUi(page, CUSTOMER_EMAIL);
  80  | 
  81  |     await page.goto("/cart/", { waitUntil: "domcontentloaded" });
> 82  |     await expect(page.getByRole("heading", { name: "Giỏ hàng của bạn." })).toBeVisible();
      |                                                                            ^ Error: expect(locator).toBeVisible() failed
  83  |     await expect(page.getByText("Redmi Note 13 Pro", { exact: true })).toBeVisible();
  84  |     await expect(page.getByText("iPhone 15 Pro Max", { exact: true })).toBeVisible();
  85  | 
  86  |     const firstQuantity = page
  87  |       .locator('button[aria-label="Increase quantity"]')
  88  |       .first()
  89  |       .locator("xpath=preceding-sibling::span[1]");
  90  |     await Promise.all([
  91  |       page.waitForResponse((response) =>
  92  |         response.url().includes("/cart/api/v1/cart/items/") &&
  93  |         response.url().includes("/quantity/") &&
  94  |         response.request().method() === "PATCH" &&
  95  |         response.ok()
  96  |       ),
  97  |       page.getByLabel("Increase quantity").first().click(),
  98  |     ]);
  99  |     await expect(firstQuantity).toHaveText("2", { timeout: 15_000 });
  100 | 
  101 |     await page.getByRole("link", { name: "Tiến hành thanh toán" }).click();
  102 |     await expect(page.getByRole("heading", { name: "Checkout" })).toBeVisible();
  103 | 
  104 |     await submitAddressForm(page, {
  105 |       receiver_name: "John Doe",
  106 |       receiver_phone: "+84912345680",
  107 |       line1: "123 Demo Street",
  108 |       district: "District 1",
  109 |       city: "Ho Chi Minh City",
  110 |       country: "Vietnam",
  111 |     });
  112 |     await Promise.all([
  113 |       page.waitForURL(/\/orders\/[^/?]+/),
  114 |       page.getByRole("button", { name: "Tạo đơn hàng" }).click(),
  115 |     ]);
  116 | 
  117 |     await expect(page.getByText("Don hang da tao thanh cong.")).toBeVisible();
  118 |     const createdOrderNumber = await page.locator("h1").textContent();
  119 |     expect(createdOrderNumber).toContain("ORD-");
  120 |     await expect(page.getByRole("button", { name: "Mock Pay Success" })).toBeVisible();
  121 |     await expect(page.getByText("awaiting_payment", { exact: true })).toBeVisible();
  122 |     await expect(page.getByText("pending", { exact: true })).toBeVisible();
  123 |     await expect(page.getByText("unfulfilled", { exact: true })).toBeVisible();
  124 |     await Promise.all([
  125 |       page.waitForResponse((response) =>
  126 |         response.url().includes("/payment/api/v1/webhooks/mock/") &&
  127 |         response.request().method() === "POST" &&
  128 |         response.ok()
  129 |       ),
  130 |       page.getByRole("button", { name: "Mock Pay Success" }).click(),
  131 |     ]);
  132 | 
  133 |     await expect(page.getByRole("heading", { name: "Lịch sử trạng thái" })).toBeVisible();
  134 | 
  135 |     await page.goto("/orders/", { waitUntil: "domcontentloaded" });
  136 |     await expect(page.getByText(String(createdOrderNumber))).toBeVisible();
  137 | 
  138 |     const createdOrderCard = page.locator("article").filter({ hasText: String(createdOrderNumber) }).first();
  139 |     await createdOrderCard.getByRole("link", { name: "Xem chi tiết" }).click();
  140 |     await expect(page.getByRole("heading", { name: String(createdOrderNumber) })).toBeVisible();
  141 |     await expect(page.getByRole("button", { name: "Mock Pay Fail" })).toBeVisible();
  142 |   }));
  143 | 
  144 | test("chat surfaces and profile data render for the seeded customer", async ({ page }) =>
  145 |   withNoServerErrors(page, async () => {
  146 |     await loginThroughUi(page, CUSTOMER_EMAIL);
  147 | 
  148 |     await page.goto("/chat/", { waitUntil: "domcontentloaded" });
  149 |     await expect(page.getByRole("heading", { name: "AI Assistant" })).toBeVisible();
  150 |     await page.getByRole("button", { name: "Đơn hàng của tôi đang ở đâu?" }).click();
  151 |     await page.getByPlaceholder("Nhap cau hoi...").fill("Đơn hàng của tôi đang ở đâu?");
  152 |     await page.getByRole("button", { name: "Gui" }).click();
  153 |     await expect(page.getByText("AI Assistant").first()).toBeVisible();
  154 |     await expect(page.getByRole("button", { name: "Đơn hàng của tôi đang ở đâu?" })).toBeVisible();
  155 |     await expect(page.locator("div.rounded-2xl").filter({ hasText: "Đơn hàng của tôi đang ở đâu?" }).last()).toBeVisible();
  156 | 
  157 |     await page.goto("/profile/", { waitUntil: "domcontentloaded" });
  158 |     await expect(page.getByRole("heading", { name: "Hồ sơ tài khoản" })).toBeVisible();
  159 |     await expect(page.getByText("Họ tên: John Doe", { exact: true })).toBeVisible();
  160 |     await expect(page.getByText("Email: john@example.com", { exact: true })).toBeVisible();
  161 |     await expect(page.getByText("Chưa có địa chỉ nào.")).toBeVisible();
  162 |   }));
  163 | 
  164 | test("admin gating blocks customers and admin CRUD remains functional", async ({ page }) =>
  165 |   withNoServerErrors(page, async () => {
  166 |     await loginThroughUi(page, CUSTOMER_EMAIL);
  167 |     await page.goto("/admin/", { waitUntil: "domcontentloaded" });
  168 |     await expect(page.getByRole("heading", { name: "Bạn không có quyền truy cập khu vực Admin." })).toBeVisible();
  169 | 
  170 |     await loginThroughUi(page, ADMIN_EMAIL);
  171 |     await page.goto("/admin/", { waitUntil: "domcontentloaded" });
  172 |     await expect(page.getByRole("heading", { name: "Admin Dashboard" })).toBeVisible();
  173 |     await expect(page.getByRole("heading", { name: "Quản lý đơn hàng" })).toBeVisible();
  174 | 
  175 |     const productName = `Playwright Demo ${Date.now()}`;
  176 |     const productSlug = `playwright-demo-${Date.now()}`;
  177 |     const updatedName = `${productName} Updated`;
  178 | 
  179 |     const form = page.getByRole("heading", { name: "Tạo sản phẩm mới" }).locator("xpath=..");
  180 |     await form.getByPlaceholder("Tên sản phẩm").fill(productName);
  181 |     await form.getByPlaceholder("Slug").fill(productSlug);
  182 |     await form.getByPlaceholder("Mô tả ngắn").fill("Product created by Playwright.");
```