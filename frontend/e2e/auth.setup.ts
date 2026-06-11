import { test as setup } from "@playwright/test";

import { type Rol } from "./env";
import { loginComo, storageStatePath } from "./helpers/auth";

// Proyecto "setup": loguea una vez por rol vía la UI real y guarda el storageState
// (cookies httpOnly) para que los tests arranquen ya autenticados, sin re-loguear.
for (const rol of ["admin", "cajero"] as Rol[]) {
  setup(`autentica ${rol}`, async ({ page }) => {
    await loginComo(page, rol);
    await page.context().storageState({ path: storageStatePath(rol) });
  });
}
