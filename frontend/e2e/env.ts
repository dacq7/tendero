// Entorno compartido por el global-setup (seed) y los webServers de Playwright.
// La base e2e es DEDICADA (`tendero_e2e`): nunca la de desarrollo ni la unit.
// Estos secretos son de PRUEBA (mock); el hardening Fase 6 B.1 los exige presentes
// para que el backend arranque. APP_ENV=test evita la guarda anti-producción.

export const E2E_DATABASE_URL =
  process.env.E2E_DATABASE_URL ??
  "postgresql+psycopg://tendero:tendero@localhost:5436/tendero_e2e";

// Puertos DEDICADOS a e2e (distintos de los de desarrollo 8020/3001): así Playwright
// nunca reutiliza por accidente un servidor de dev apuntando a la base de desarrollo.
export const BACKEND_PORT = 8021;
export const FRONTEND_PORT = 3002;
export const BACKEND_URL = `http://localhost:${BACKEND_PORT}`;
export const FRONTEND_URL = `http://localhost:${FRONTEND_PORT}`;

// Env del backend e2e (uvicorn) y del proceso de seed.
export const backendEnv: Record<string, string> = {
  DATABASE_URL: E2E_DATABASE_URL,
  APP_ENV: "test",
  JWT_SECRET: "e2e_jwt_secret_no_real_solo_para_pruebas",
  WOMPI_PROVIDER: "mock",
  WOMPI_INTEGRITY_SECRET: "integrity_test_secret",
  WOMPI_EVENTS_SECRET: "events_test_secret",
  FISCAL_PROVIDER: "mock",
  FISCAL_CUFE_SECRET: "cufe_demo_secret",
  FRONTEND_ORIGIN: FRONTEND_URL,
};

// Credenciales sembradas por backend/app/seed_e2e.py.
export const USERS = {
  admin: { email: "admin@e2e.co", password: "E2e1234!", nombre: "Admin E2E" },
  cajero: { email: "cajero@e2e.co", password: "E2e1234!", nombre: "Cajero E2E" },
} as const;

export type Rol = keyof typeof USERS;
