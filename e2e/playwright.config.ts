import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  retries: 0,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:5174',
    headless: true,
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  // Start the Vite dev server and FastAPI backend before tests run
  webServer: [
    {
      command: 'npm run dev -- --port 5174',
      cwd: '../frontend',
      url: 'http://localhost:5174',
      reuseExistingServer: true,
      timeout: 30_000,
    },
    {
      command: 'python -m uvicorn main:app --port 8000',
      cwd: '../backend',
      url: 'http://localhost:8000/health',
      reuseExistingServer: true,
      timeout: 20_000,
    },
  ],
})
