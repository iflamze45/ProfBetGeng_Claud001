import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 30000,
  use: {
    baseURL: 'http://localhost:5299',
    headless: true,
  },
  webServer: {
    command: 'npm run dev -- --port 5299',
    url: 'http://localhost:5299',
    reuseExistingServer: !process.env.CI,
    timeout: 30000,
  },
})
