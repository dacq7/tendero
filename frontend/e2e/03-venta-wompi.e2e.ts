import { expect, test } from "@playwright/test";

import { storageStatePath } from "./helpers/auth";
import { abrirCaja } from "./helpers/caja";
import { agregarProducto, cobrar } from "./helpers/vender";

// Flujo 3 — Pago asíncrono Wompi (mock): aprobado → ticket; rechazado → reverso.
test.use({ storageState: storageStatePath("cajero") });

test("tarjeta aprobada: procesando → ticket", async ({ page }) => {
  await abrirCaja(page);
  await agregarProducto(page, "Agua E2E");
  await cobrar(page, "Tarjeta");

  // Estado intermedio async.
  await expect(page.getByText("Procesando pago")).toBeVisible();
  await expect(page.getByText("Modo demo — simular resultado")).toBeVisible();

  // Simular aprobación → ticket.
  await page.getByRole("button", { name: "Aprobar" }).click();
  await expect(page.getByRole("button", { name: "Nueva venta" })).toBeVisible();
  await expect(page.getByText(/POS-\d{6}/)).toBeVisible();
});

test("tarjeta rechazada: procesando → rechazo con reverso de stock", async ({ page }) => {
  await abrirCaja(page);
  await agregarProducto(page, "Agua E2E");
  await cobrar(page, "Tarjeta");

  await expect(page.getByText("Procesando pago")).toBeVisible();
  await page.getByRole("button", { name: "Rechazar" }).click();

  await expect(page.getByText("Pago rechazado")).toBeVisible();
  await expect(page.getByText(/stock se devolvió al inventario/)).toBeVisible();
});
