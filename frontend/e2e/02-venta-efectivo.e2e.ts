import { expect, test } from "@playwright/test";

import { storageStatePath } from "./helpers/auth";
import { abrirCaja } from "./helpers/caja";
import { agregarProducto, cobrar } from "./helpers/vender";

// Flujo 2 — Venta en efectivo de punta a punta (el corazón del producto).
test.use({ storageState: storageStatePath("cajero") });

test("venta efectivo: carrito → cobro → ticket → historial → caja", async ({ page }) => {
  await abrirCaja(page, 100000);

  // Agregar desde la grilla.
  await agregarProducto(page, "Gaseosa E2E");

  // La cantidad sube en ENTEROS (1 → 2 unidades), no en milésimas.
  const qty = page.getByRole("spinbutton");
  await expect(qty).toHaveValue("1");
  await page.getByRole("button", { name: "Sumar Gaseosa E2E" }).click();
  await expect(qty).toHaveValue("2");

  // El total del carrito se calcula en vivo (no vacío, no cero).
  await expect(page.getByTestId("cart-total")).not.toHaveText("");
  await expect(page.getByTestId("cart-total")).not.toHaveText(/\$\s*0$/);

  // Cobrar en efectivo y ver el ticket con número de factura.
  await cobrar(page, "Efectivo");
  await expect(page.getByRole("button", { name: "Nueva venta" })).toBeVisible();
  const numero = await page.getByText(/POS-\d{6}/).first().textContent();
  expect(numero).toMatch(/POS-\d{6}/);

  // Aparece en el Historial.
  await page.goto("/historial");
  await expect(page.getByText(numero!.trim())).toBeVisible();

  // La caja refleja al menos esa transacción del turno.
  await page.goto("/caja");
  await page.getByRole("button", { name: "Refrescar" }).click();
  await expect(page.getByTestId("n-tx")).toHaveText(/[1-9]\d*/);
});
