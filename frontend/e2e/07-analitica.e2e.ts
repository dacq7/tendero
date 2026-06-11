import { expect, test } from "@playwright/test";

import { storageStatePath } from "./helpers/auth";

// Flujo 7 — Analítica (admin): el dashboard carga y las pestañas cambian sin error.
// No se asertan cifras exactas (dependen del seed + ventas del run) para evitar
// flakiness; se verifica que el render de KPIs y la conmutación de pestañas funcionan.
test.use({ storageState: storageStatePath("admin") });

test("el dashboard carga KPIs y cambia de pestaña", async ({ page }) => {
  await page.goto("/analitica");
  await expect(page.getByRole("heading", { name: "Analítica" })).toBeVisible();

  // Rango "Este año": garantiza datos (incluye la venta histórica sembrada), así el
  // Resumen muestra KPIs en vez del estado "Sin datos en este periodo".
  await page.getByRole("button", { name: "Este año" }).click();

  // Pestaña Resumen: los cuatro KPIs renderizan.
  for (const kpi of ["Ventas", "Transacciones", "Ticket promedio", "Margen"]) {
    await expect(page.getByText(kpi, { exact: true })).toBeVisible();
  }

  // Conmutar a Rentabilidad: la pestaña queda activa y carga su panel.
  await page.getByRole("button", { name: "Rentabilidad" }).click();
  await expect(page.getByRole("button", { name: "Rentabilidad" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  await expect(
    page.getByRole("heading", { name: "Rentabilidad por producto" }),
  ).toBeVisible();
});
