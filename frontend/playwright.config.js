import { defineConfig, devices } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const pythonPath = path.resolve(__dirname, '..', 'backend', '.venv', 'Scripts', 'python.exe');
const serverScript = path.resolve(__dirname, '..', 'backend', 'run_e2e_server.py');

export default defineConfig({
  testDir: './e2e',
  timeout: 360000,
  expect: {
    timeout: 30000,
  },
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:5174',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: `"${pythonPath}" "${serverScript}"`,
      url: 'http://127.0.0.1:8001/health/e2e',
      reuseExistingServer: false,
      timeout: 60000,
    },
    {
      command: 'npx vite --port 5174 --host 127.0.0.1',
      url: 'http://127.0.0.1:5174',
      reuseExistingServer: false,
      timeout: 30000,
      env: {
        VITE_API_BASE_URL: 'http://127.0.0.1:8001',
      },
    },
  ],
});

