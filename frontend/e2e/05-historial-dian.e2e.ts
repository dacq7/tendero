import { expect, test } from "@playwright/test";

import { storageStatePath } from "./helpers/auth";

// Flujo 5 — Historial + emisión DIAN (mock). La venta histórica sembrada es la
// factura POS-000001 (sin emitir), objetivo determinista de este flujo.
const FACTURA = "POS-000001";

test.describe("admin emite a DIAN", () => {
  test.use({ storageState: storageStatePath("admin") });

  test("emitir desde el historial deja la factura Aceptada con CUFE", async ({ page }) => {
    await page.goto("/historial");

    const fila = page.getByRole("row", { name: new RegExp(FACTURA) });
    await expect(fila).toBeVisible();
    await expect(fila.getByText("Sin emitir")).toBeVisible();

    await fila.getByRole("button", { name: "Emitir a DIAN" }).click();

    // El mock acepta (totales cuadran): badge a "Aceptada" + CUFE visible.
    await expect(fila.getByText("Aceptada")).toBeVisible();
    await expect(fila.getByText(/CUFE/)).toBeVisible();
  });

  test("el detalle muestra estado DIAN aceptado, CUFE y snapshots", async ({ page }) => {
    await page.goto("/historial");
    await page.getByRole("link", { name: FACTURA }).click();
    await expect(page).toHaveURL(/\/historial\/\d+/);

    // Panel Factura / DIAN.
    await expect(page.getByText("Estado DIAN")).toBeVisible();
    await expect(page.getByText("Aceptada")).toBeVisible();
    await expect(page.getByText(/CUFE/)).toBeVisible();
    // Snapshot del item vendido (Gaseosa E2E).
    await expect(page.getByText("Gaseosa E2E")).toBeVisible();
  });
});

test.describe("cajero no puede emitir", () => {
  test.use({ storageState: storageStatePath("cajero") });

  test("el cajero no ve el botón Emitir a DIAN", async ({ page }) => {
    await page.goto("/historial");
    await expect(page.getByText("Historial de facturas")).toBeVisible();
    await expect(page.getByRole("button", { name: "Emitir a DIAN" })).toHaveCount(0);
  });
});
