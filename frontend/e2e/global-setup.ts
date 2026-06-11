import { execFileSync } from "node:child_process";
import path from "node:path";

import { backendEnv } from "./env";

// Crea/migra/siembra la base e2e ANTES de levantar los webServers, ejecutando el seed
// determinista del backend (`python -m app.seed_e2e`) con la env e2e. Una sola vez por
// corrida; el seed hace DROP/CREATE de `tendero_e2e`, así que cada run parte limpio.
export default async function globalSetup() {
  const backendDir = path.resolve(__dirname, "../../backend");
  const python = path.join(backendDir, ".venv", "bin", "python");
  execFileSync(python, ["-m", "app.seed_e2e"], {
    cwd: backendDir,
    env: { ...process.env, ...backendEnv },
    stdio: "inherit",
  });
}
