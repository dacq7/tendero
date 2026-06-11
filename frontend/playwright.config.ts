import { defineConfig, devices } from "@playwright/test";

import { backendEnv, BACKEND_URL, FRONTEND_URL } from "./e2e/env";

// Tests e2e de Tendero: navegador real contra el stack completo (Next BFF → proxy →
// FastAPI → Postgres). La DB es la base AISLADA `tendero_e2e`, creada/migrada/sembrada
// por `globalSetup` antes de levantar los servidores.
//
// Coexistencia con Vitest: estos viven en `e2e/` con sufijo `.e2e.ts`; Vitest solo
// recoge `src/**/*.test.{ts,tsx}`.
export default defineConfig({
  testDir: "./e2e",
  testMatch: "**/*.e2e.ts",
  // El backend impone "una sola caja abierta a la vez" y numeración POS global:
  // correr en serie evita carreras estructurales y flakiness.
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  globalSetup: "./e2e/global-setup.ts",

  use: {
    baseURL: FRONTEND_URL,
    trace: "on-first-retry",
    // Espera por defecto de acciones/aserciones: explícita, sin sleeps fijos.
    actionTimeout: 10_000,
  },

  projects: [
    // Genera los storageState por rol (login real por la UI) una sola vez.
    { name: "setup", testMatch: /auth\.setup\.ts/ },
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
      dependencies: ["setup"],
      testMatch: "**/*.e2e.ts",
    },
  ],

  webServer: [
    {
      // Backend FastAPI (puerto e2e 8021) con la env e2e: DB aislada + secretos de
      // prueba requeridos por el hardening Fase 6 B.1.
      command: ".venv/bin/uvicorn app.main:app --port 8021",
      cwd: "../backend",
      url: `${BACKEND_URL}/health`,
      env: backendEnv,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      stdout: "pipe",
      stderr: "pipe",
    },
    {
      // Frontend Next (puerto e2e 3002); el BFF habla con el backend e2e server-side.
      command: "npm run dev -- --port 3002",
      url: FRONTEND_URL,
      env: { BACKEND_URL, NEXT_PUBLIC_API_URL: BACKEND_URL },
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
