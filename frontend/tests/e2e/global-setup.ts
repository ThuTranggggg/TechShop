const HEALTHCHECK_URLS = [
  "http://localhost:8080/health/",
  "http://localhost:8080/user/health/",
  "http://localhost:8080/product/health/",
  // /cart/ is a storefront page now, so probe the cart service directly.
  "http://localhost:8003/health/",
  "http://localhost:8080/order/health/",
  "http://localhost:8080/payment/health/",
  "http://localhost:8080/shipping/health/",
  "http://localhost:8080/inventory/health/",
  "http://localhost:8080/ai/health/",
];

async function waitForOk(url: string, timeoutMs = 120_000) {
  const startedAt = Date.now();
  let lastError = "";

  while (Date.now() - startedAt < timeoutMs) {
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(5_000) });
      if (response.ok) return;
      lastError = `${response.status} ${response.statusText}`;
    } catch (error) {
      lastError = error instanceof Error ? error.message : String(error);
    }

    await new Promise((resolve) => setTimeout(resolve, 2_000));
  }

  throw new Error(`Timed out waiting for ${url}. Last error: ${lastError || "unknown"}`);
}

export default async function globalSetup() {
  for (const url of HEALTHCHECK_URLS) {
    await waitForOk(url);
  }
}
