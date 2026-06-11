import { expect, type Page } from "@playwright/test";

// El backend permite UNA sola caja abierta a la vez (validación global). Estos
// helpers mantienen el estado de caja determinista entre tests seriales.

const ABRIR = /^Abrir caja/;
const CERRAR = /^Cerrar caja/;

// Navega a /caja y ESPERA a que el estado async cargue (botón Abrir, o turno abierto):
// sin esto, un check de visibilidad inmediato corre antes del render y da falsos
// negativos (la página resuelve la sesión actual con un fetch).
async function irACajaConEstadoCargado(page: Page) {
  await page.goto("/caja");
  const abrir = page.getByRole("button", { name: ABRIR });
  const turnoAbierto = page.getByText("Caja abierta · turno actual");
  await expect(abrir.or(turnoAbierto).first()).toBeVisible();
  return { abrir, turnoAbierto };
}

// Cierra la caja si hay una abierta (arqueo con 0 contado; la diferencia da igual
// para los tests que solo necesitan dejar la caja cerrada).
export async function cerrarCajaSiAbierta(page: Page): Promise<void> {
  const { turnoAbierto } = await irACajaConEstadoCargado(page);
  if (await turnoAbierto.isVisible()) {
    await page.getByLabel("Efectivo contado (arqueo)").fill("0");
    await page.getByRole("button", { name: CERRAR }).click();
    await expect(page.getByText("Caja cerrada — arqueo")).toBeVisible();
  }
}

// Abre una caja con el monto inicial dado (en PESOS). Si ya hay una abierta, no hace
// nada (reutiliza la existente).
export async function abrirCaja(page: Page, montoInicialPesos = 100000): Promise<void> {
  const { abrir, turnoAbierto } = await irACajaConEstadoCargado(page);
  if (await turnoAbierto.isVisible()) return; // ya hay caja abierta
  await page.getByLabel("Monto inicial (base)").fill(String(montoInicialPesos));
  await abrir.click();
  await expect(page.getByText("Caja abierta · turno actual")).toBeVisible();
}

// Deja una caja FRESCA y conocida: cierra la previa (si la hay) y abre una nueva.
export async function abrirCajaFresca(page: Page, montoInicialPesos = 100000): Promise<void> {
  await cerrarCajaSiAbierta(page);
  await abrirCaja(page, montoInicialPesos);
}
