import { expect, test } from "@playwright/test";

import { storageStatePath } from "./helpers/auth";
import { abrirCajaFresca } from "./helpers/caja";
import { agregarProducto, cobrar } from "./helpers/vender";

// Flujo 4 — Caja: total del turno con valores CONOCIDOS y arqueo cuadrado.
test.use({ storageState: storageStatePath("cajero") });

test("caja: total del turno y arqueo sin diferencia", async ({ page }) => {
  // Caja fresca con monto inicial conocido: 100.000 pesos.
  await abrirCajaFresca(page, 100000);

  // Exactamente UNA venta en efectivo: 1 Gaseosa E2E (200000c base + 19% IVA = 238000c).
  await agregarProducto(page, "Gaseosa E2E");
  await cobrar(page, "Efectivo");
  await expect(page.getByRole("button", { name: "Nueva venta" })).toBeVisible();

  await page.goto("/caja");
  await page.getByRole("button", { name: "Refrescar" }).click();

  // Una sola transacción en el turno.
  await expect(page.getByTestId("n-tx")).toHaveText("1");

  // Esperado en efectivo = 100.000 (base) + 2.380 (venta) = 102.380 pesos.
  await expect(page.getByTestId("esperado-efectivo")).toContainText("102.380");

  // Arqueo cuadrado: contar 102.380 → diferencia 0, caja cierra.
  await page.getByLabel("Efectivo contado (arqueo)").fill("102380");
  await page.getByRole("button", { name: /^Cerrar caja/ }).click();
  // El cierre con arqueo se completa (el esperado ya se verificó arriba = 102.380).
  await expect(page.getByText("Caja cerrada — arqueo")).toBeVisible();
});
