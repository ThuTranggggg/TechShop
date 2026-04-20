import { expect, type Page } from "@playwright/test";

const DEFAULT_PASSWORD = "Demo@123456";

export function uniqueEmail(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}@example.com`;
}

export async function withNoServerErrors(page: Page, run: () => Promise<void>) {
  const failures: Array<{ status: number; url: string }> = [];
  const onResponse = (response: { status: () => number; url: () => string }) => {
    const status = response.status();
    if (status >= 500) {
      failures.push({ status, url: response.url() });
    }
  };

  page.on("response", onResponse);

  try {
    await run();
  } finally {
    page.off("response", onResponse);
    expect(failures, failures.map((failure) => `${failure.status} ${failure.url}`).join("\n")).toEqual([]);
  }
}

export async function loginThroughUi(page: Page, email: string, password = DEFAULT_PASSWORD) {
  await page.goto("/login");
  const inputs = page.locator("input");
  await inputs.nth(0).fill(email);
  await inputs.nth(1).fill(password);
  await Promise.all([
    page.waitForURL("**/"),
    page.getByRole("button", { name: "Đăng nhập" }).click(),
  ]);
  await expect(page.getByRole("heading", { name: "Mua sắm công nghệ gọn, đẹp và có AI hỗ trợ." })).toBeVisible();
}

export async function registerThroughUi(page: Page, payload: {
  full_name: string;
  email: string;
  password: string;
  phone_number?: string;
}) {
  await page.goto("/register");
  const inputs = page.locator("input");
  await inputs.nth(0).fill(payload.full_name);
  await inputs.nth(1).fill(payload.email);
  await inputs.nth(2).fill(payload.phone_number ?? "");
  await inputs.nth(3).fill(payload.password);
  await inputs.nth(4).fill(payload.password);
  await Promise.all([
    page.waitForURL("**/"),
    page.getByRole("button", { name: "Đăng ký" }).click(),
  ]);
  await expect(page.getByRole("heading", { name: "Mua sắm công nghệ gọn, đẹp và có AI hỗ trợ." })).toBeVisible();
}

export async function submitAddressForm(page: Page, values: {
  receiver_name: string;
  receiver_phone: string;
  line1: string;
  district: string;
  city: string;
  country?: string;
}) {
  await page.getByPlaceholder("Người nhận").fill(values.receiver_name);
  await page.getByPlaceholder("Số điện thoại").fill(values.receiver_phone);
  await page.getByPlaceholder("Địa chỉ").fill(values.line1);
  await page.getByPlaceholder("Quận/Huyện").fill(values.district);
  await page.getByPlaceholder("Thành phố").fill(values.city);
  await page.getByPlaceholder("Quốc gia").fill(values.country ?? "Vietnam");
}
