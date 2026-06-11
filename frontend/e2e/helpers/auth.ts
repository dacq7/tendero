import path from "node:path";

import { expect, type Page } from "@playwright/test";

import { USERS, type Rol } from "../env";

// Ruta del storageState (cookies httpOnly de sesión) por rol.
export function storageStatePath(rol: Rol): string {
  return path.join(__dirname, "..", ".auth", `${rol}.json`);
}

// Login REAL por la UI (las cookies son httpOnly: no se pueden inyectar). Ejercita
// el BFF completo: form → /api/session → backend → cookies.
export async function loginComo(page: Page, rol: Rol): Promise<void> {
  const { email, password } = USERS[rol];
  await page.goto("/login");
  await page.locator("#email").fill(email);
  await page.locator("#password").fill(password);
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page).toHaveURL(/\/vender/);
}
