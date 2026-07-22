import { defineConfig } from "@playwright/test";

const baseURL = process.env.AAC_WEB_BASE_URL;

if (!baseURL) {
  throw new Error("AAC_WEB_BASE_URL is required for real-stack browser tests");
}

export default defineConfig({
  testDir: ".",
  testMatch: /.*\.spec\.js/,
  timeout: 45_000,
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL,
    browserName: "chromium",
    trace: "retain-on-failure",
  },
});
