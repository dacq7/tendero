import { expect, test } from "@playwright/test";

import { storageStatePath } from "./helpers/auth";

// Flujo 1 — Autenticación y guard de roles.

test.describe("sin sesión", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("una ruta protegida redirige a /login", async ({ page }) => {
    await page.goto("/vender");
    await expect(page).toHaveURL(/\/login/);
  });

  test("credenciales inválidas muestran el error", async ({ page }) => {
    await page.goto("/login");
    await page.locator("#email").fill("admin@e2e.co");
    await page.locator("#password").fill("clave-incorrecta");
    await page.getByRole("button", { name: "Entrar" }).click();
    // getByText (no getByRole("alert")): la app monta además un alert vacío de las
    // Next.js Dev Tools, que haría ambiguo el rol.
    await expect(page.getByText("Correo o contraseña incorrectos.")).toBeVisible();
    await expect(page).toHaveURL(/\/login/);
  });
});

test.describe("admin autenticado", () => {
  test.use({ storageState: storageStatePath("admin") });

  test("ve el nav completo, incluido Analítica y Facturación", async ({ page }) => {
    await page.goto("/vender");
    for (const link of ["Vender", "Caja", "Inventario", "Historial", "Facturación", "Analítica"]) {
      await expect(page.getByRole("link", { name: link })).toBeVisible();
    }
  });

  test("puede cerrar sesión", async ({ page }) => {
    await page.goto("/vender");
    await page.getByRole("button", { name: "Salir" }).click();
    await expect(page).toHaveURL(/\/login/);
  });
});

test.describe("cajero autenticado", () => {
  test.use({ storageState: storageStatePath("cajero") });

  test("NO ve las secciones admin-only", async ({ page }) => {
    await page.goto("/vender");
    await expect(page.getByRole("link", { name: "Vender" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Analítica" })).toHaveCount(0);
    await expect(page.getByRole("link", { name: "Facturación" })).toHaveCount(0);
  });

  test("el acceso directo a /analitica muestra el guard de admin", async ({ page }) => {
    await page.goto("/analitica");
    await expect(
      page.getByText("Esta sección es solo para administradores."),
    ).toBeVisible();
  });
});
