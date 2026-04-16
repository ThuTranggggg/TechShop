import { expect, test } from "@playwright/test";
import {
  loginThroughUi,
  registerThroughUi,
  submitAddressForm,
  uniqueEmail,
  withNoServerErrors,
} from "./helpers";

test.describe.configure({ mode: "serial" });

const CUSTOMER_EMAIL = "john@example.com";
const ADMIN_EMAIL = "admin@example.com";
const DEMO_PASSWORD = "Demo@123456";

test("anonymous users are redirected to login from protected routes", async ({ page }) =>
  withNoServerErrors(page, async () => {
    await page.goto("/checkout");
    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByRole("heading", { name: "Đăng nhập tài khoản" })).toBeVisible();
  }));

test("registration and login work with the real auth service", async ({ page }) =>
  withNoServerErrors(page, async () => {
    const email = uniqueEmail("playwright-customer");

    await registerThroughUi(page, {
      full_name: "Playwright Customer",
      email,
      password: DEMO_PASSWORD,
      phone_number: "+84900000001",
    });

    await page.goto("/profile");
    await expect(page.getByRole("heading", { name: "Hồ sơ tài khoản" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Đăng xuất" })).toBeVisible();

    await page.getByRole("button", { name: "Đăng xuất" }).click();
    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByRole("heading", { name: "Đăng nhập tài khoản" })).toBeVisible();

    await loginThroughUi(page, CUSTOMER_EMAIL);
    await page.goto("/profile");
    await expect(page.getByText("Họ tên: John Doe", { exact: true })).toBeVisible();
  }));

test("home and catalog surfaces render seeded products and recommendations", async ({ page }) =>
  withNoServerErrors(page, async () => {
    await loginThroughUi(page, CUSTOMER_EMAIL);

    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Mua sắm công nghệ theo cách hoàn toàn mới." })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Sản phẩm nổi bật" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "iPhone 15" }).first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Gợi ý AI cho bạn" })).toBeVisible();

    await page.goto("/products");
    await expect(page.getByRole("heading", { name: "Danh mục sản phẩm" })).toBeVisible();
    await page.getByPlaceholder("Tìm laptop, điện thoại, thương hiệu...").fill("Galaxy");
    await page.getByRole("button", { name: "Tìm" }).click();
    await expect(page.getByRole("heading", { name: "Galaxy S24" }).first()).toBeVisible();

    await page.locator("aside").getByRole("combobox").first().selectOption({ label: "Dien thoai" });
    await page.locator("aside").getByRole("combobox").nth(1).selectOption({ label: "Samsung" });
    await page.getByText("Sắp xếp").locator("..").getByRole("combobox").selectOption("-base_price");
    await expect(page.getByRole("heading", { name: "Galaxy S24" }).first()).toBeVisible();

    await Promise.all([
      page.waitForURL(/\/products\/[^/]+$/),
      page.getByRole("link", { name: "Galaxy S24", exact: true }).click(),
    ]);
    await expect(page.locator("h1")).toContainText("Galaxy S24", { timeout: 10_000 });
    await expect(page.getByText("Galaxy S24 - demo product", { exact: true })).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole("heading", { name: "Sản phẩm liên quan" })).toBeVisible({ timeout: 10000 });
  }));

test("cart, checkout, and order detail flows work through the gateway", async ({ page }) =>
  withNoServerErrors(page, async () => {
    await loginThroughUi(page, CUSTOMER_EMAIL);

    await page.goto("/cart/", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: "Giỏ hàng của bạn." })).toBeVisible();
    await expect(page.getByText("Redmi Note 13 Pro", { exact: true })).toBeVisible();
    await expect(page.getByText("iPhone 15 Pro Max", { exact: true })).toBeVisible();

    const iphoneRow = page.getByText("iPhone 15 Pro Max", { exact: true }).locator("xpath=ancestor::div[contains(@class,'card-premium')][1]");
    const iphoneQuantity = iphoneRow.locator("span.w-10.text-center.text-sm.font-semibold");
    await Promise.all([
      page.waitForResponse((response) =>
        response.url().includes("/cart/api/v1/cart/items/") &&
        response.url().includes("/quantity/") &&
        response.request().method() === "PATCH" &&
        response.ok()
      ),
      iphoneRow.getByRole("button", { name: "Increase quantity" }).click(),
    ]);
    await page.reload({ waitUntil: "domcontentloaded" });
    await expect(iphoneQuantity).toHaveText("2", { timeout: 15_000 });

    await page.getByRole("link", { name: "Tiến hành thanh toán" }).click();
    await expect(page.getByRole("heading", { name: "Checkout" })).toBeVisible();

    await submitAddressForm(page, {
      receiver_name: "John Doe",
      receiver_phone: "+84912345680",
      line1: "123 Demo Street",
      district: "District 1",
      city: "Ho Chi Minh City",
      country: "Vietnam",
    });
    await Promise.all([
      page.waitForURL(/\/orders\/[^/?]+/),
      page.getByRole("button", { name: "Tạo đơn hàng" }).click(),
    ]);

    await expect(page.getByText("Don hang da tao thanh cong.")).toBeVisible();
    const createdOrderNumber = await page.locator("h1").textContent();
    expect(createdOrderNumber).toContain("ORD-");
    await expect(page.getByRole("button", { name: "Mock Pay Success" })).toBeVisible();
    await expect(page.getByText("awaiting_payment", { exact: true })).toBeVisible();
    await expect(page.getByText("pending", { exact: true })).toBeVisible();
    await expect(page.getByText("unfulfilled", { exact: true })).toBeVisible();
    await Promise.all([
      page.waitForResponse((response) =>
        response.url().includes("/payment/api/v1/webhooks/mock/") &&
        response.request().method() === "POST" &&
        response.ok()
      ),
      page.getByRole("button", { name: "Mock Pay Success" }).click(),
    ]);

    await expect(page.getByRole("heading", { name: "Lịch sử trạng thái" })).toBeVisible();

    await page.goto("/orders/", { waitUntil: "domcontentloaded" });
    await expect(page.getByText(String(createdOrderNumber))).toBeVisible();

    const createdOrderCard = page.locator("article").filter({ hasText: String(createdOrderNumber) }).first();
    await createdOrderCard.getByRole("link", { name: "Xem chi tiết" }).click();
    await expect(page.getByRole("heading", { name: String(createdOrderNumber) })).toBeVisible();
    await expect(page.getByRole("button", { name: "Mock Pay Fail" })).toBeVisible();
  }));

test("chat surfaces and profile data render for the seeded customer", async ({ page }) =>
  withNoServerErrors(page, async () => {
    await loginThroughUi(page, CUSTOMER_EMAIL);

    await page.goto("/chat/", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: "AI Assistant" })).toBeVisible();
    await page.getByRole("button", { name: "Đơn hàng của tôi đang ở đâu?" }).click();
    await page.getByPlaceholder("Nhap cau hoi...").fill("Đơn hàng của tôi đang ở đâu?");
    await page.getByRole("button", { name: "Gui" }).click();
    await expect(page.getByText("AI Assistant").first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Đơn hàng của tôi đang ở đâu?" })).toBeVisible();
    await expect(page.locator("div.rounded-2xl").filter({ hasText: "Đơn hàng của tôi đang ở đâu?" }).last()).toBeVisible();

    await page.goto("/profile/", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: "Hồ sơ tài khoản" })).toBeVisible();
    await expect(page.getByText("Họ tên: John Doe", { exact: true })).toBeVisible();
    await expect(page.getByText("Email: john@example.com", { exact: true })).toBeVisible();
    await expect(page.getByText("Chưa có địa chỉ nào.")).toBeVisible();
  }));

test("admin gating blocks customers and admin CRUD remains functional", async ({ page }) =>
  withNoServerErrors(page, async () => {
    await loginThroughUi(page, CUSTOMER_EMAIL);
    await page.goto("/admin/", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: "Bạn không có quyền truy cập khu vực Admin." })).toBeVisible();

    await loginThroughUi(page, ADMIN_EMAIL);
    await page.goto("/admin/", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: "Admin Dashboard" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Quản lý đơn hàng" })).toBeVisible();

    const productName = `Playwright Demo ${Date.now()}`;
    const productSlug = `playwright-demo-${Date.now()}`;
    const updatedName = `${productName} Updated`;

    const form = page.getByRole("heading", { name: "Tạo sản phẩm mới" }).locator("xpath=..");
    await form.getByPlaceholder("Tên sản phẩm").fill(productName);
    await form.getByPlaceholder("Slug").fill(productSlug);
    await form.getByPlaceholder("Mô tả ngắn").fill("Product created by Playwright.");
    await form.getByPlaceholder("Mô tả chi tiết").fill("Playwright created this product in the real stack.");
    await form.getByPlaceholder("Ảnh thumbnail URL").fill("https://images.unsplash.com/photo-1517336714739-489689fd1ca8?w=1200");
    await form.locator("select").nth(0).selectOption({ label: "Dien thoai" });
    await form.locator("select").nth(1).selectOption({ label: "Apple" });
    await form.locator("select").nth(2).selectOption({ label: "Phone" });
    await form.getByRole("button", { name: "Tạo mới" }).click();
    await expect(page.getByText(productName)).toBeVisible();

    const createdCard = page.locator("article").filter({ hasText: productName }).first();
    await createdCard.getByRole("button", { name: "Sửa" }).click();
    await expect(page.getByRole("button", { name: "Cập nhật" })).toBeVisible();
    await page.locator("select").nth(0).selectOption({ label: "Dien thoai" });
    await page.locator("select").nth(1).selectOption({ label: "Apple" });
    await page.locator("select").nth(2).selectOption({ label: "Phone" });
    await page.getByPlaceholder("Tên sản phẩm").fill(updatedName);
    await page.getByRole("button", { name: "Cập nhật" }).click();
    await expect(page.getByText(updatedName)).toBeVisible();

    const updatedCard = page.locator("article").filter({ hasText: updatedName }).first();
    await updatedCard.getByRole("button", { name: "Xoá" }).click();
    await expect(page.locator("article").filter({ hasText: updatedName })).toHaveCount(0);
  }));
