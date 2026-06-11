import { expect, test } from "@playwright/test";

import { storageStatePath } from "./helpers/auth";

// Flujo 6 — Inventario (admin): crear → entrada (sube stock) → merma (baja) → kardex,
// con el invariante de que el stock NO se edita a mano.
test.use({ storageState: storageStatePath("admin") });

const NOMBRE = "Inventario E2E";
const SKU = "E2E-INV";

test("crear, entrada, merma y kardex; stock no editable", async ({ page }) => {
  // 1) Crear producto (sin stock inicial).
  await page.goto("/inventario");
  await page.getByRole("link", { name: "Nuevo producto" }).click();
  await page.getByLabel(/Nombre/).fill(NOMBRE);
  await page.getByLabel(/SKU/).fill(SKU);
  await page.getByLabel(/Precio costo/).fill("500");
  await page.getByLabel(/Precio venta/).fill("900");
  await page.getByRole("button", { name: /^Crear producto/ }).click();
  await expect(page).toHaveURL(/\/inventario(\/\d+)?$/);

  // 2) Entrada de mercancía: +10 unidades.
  await page.goto("/inventario/entradas");
  await page.getByLabel("Producto línea 1").selectOption({ label: NOMBRE });
  await page.getByLabel("Cantidad línea 1").fill("10");
  await page.getByLabel("Costo línea 1").fill("500");
  await page.getByRole("button", { name: /^Registrar entrada/ }).click();
  await expect(page.getByText(/Entrada registrada/)).toBeVisible();

  // 3) Abrir el detalle: stock subió a 10 y el kardex muestra la entrada.
  await page.goto("/inventario");
  await page.getByRole("row", { name: new RegExp(NOMBRE) }).click();
  await expect(page).toHaveURL(/\/inventario\/\d+/);
  await expect(page.getByTestId("stock-readonly")).toContainText("10");
  await expect(page.getByText(/El stock no se edita aquí/)).toBeVisible();
  // Kardex: la entrada aparece como una celda (acotado para no chocar con el texto
  // "...cambia con entradas..." del aviso de stock).
  await expect(page.getByRole("cell", { name: /^Entrada/ })).toBeVisible();

  // 4) Merma: −3 unidades → stock baja a 7; el kardex registra la merma.
  await page.getByRole("button", { name: "merma" }).click();
  await page.getByLabel("Cantidad del movimiento").fill("3");
  await page.getByLabel(/Motivo/).fill("Vencido (e2e)");
  await page.getByRole("button", { name: /^Registrar movimiento/ }).click();

  await expect(page.getByTestId("stock-readonly")).toContainText("7");
  await expect(page.getByRole("cell", { name: /^Merma/ })).toBeVisible();
});
