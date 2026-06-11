import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";
import { defineConfig } from "vitest/config";

// jsdom + Testing Library para componentes React. El alias `@/` se resuelve
// leyendo `tsconfig.json` (vite-tsconfig-paths).
export default defineConfig({
  plugins: [react(), tsconfigPaths()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    // Los e2e de Playwright (e2e/**/*.e2e.ts) NO los corre Vitest (frontera explícita).
    exclude: ["e2e/**", "node_modules/**"],
  },
});
