import { defineConfig, devices } from "@playwright/test";

const useMockBackend = process.env.PLAYWRIGHT_USE_MOCK_BACKEND === "1";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "list",
  globalSetup: useMockBackend ? undefined : "./tests/e2e/global-setup.ts",
  use: {
    baseURL: useMockBackend ? "http://localhost:3101" : "http://localhost:8080",
    trace: "on-first-retry",
  },
  webServer: useMockBackend
    ? [
        {
          command: "PORT=18181 node tests/e2e/mock-backend.mjs",
          url: "http://localhost:18181/health",
          reuseExistingServer: false,
        },
        {
          command: "API_PROXY_BASE_URL=http://localhost:18181 NEXT_PUBLIC_API_BASE_URL=/api/proxy npx next dev -p 3101",
          url: "http://localhost:3101",
          reuseExistingServer: false,
        },
      ]
    : [
        {
          command: "docker compose -f ../docker-compose.yml up --build gateway",
          url: "http://localhost:8080/health/",
          reuseExistingServer: true,
          timeout: 900_000,
        },
      ],
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
