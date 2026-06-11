import { expect, type Page } from "@playwright/test";

// Agrega un producto al carrito tocándolo en la grilla (camino de mostrador real).
export async function agregarProducto(page: Page, nombre: string): Promise<void> {
  await page.goto("/vender");
  const boton = page.getByRole("button", { name: new RegExp(nombre) });
  await expect(boton.first()).toBeVisible();
  await boton.first().click();
}

// Abre el modal de cobro, elige método y confirma. Devuelve cuando el modal procesó
// (el caller asierta el ticket o el estado async según el método).
export async function cobrar(page: Page, metodo: string): Promise<void> {
  await page.getByRole("button", { name: "Cobrar" }).click();
  const dialog = page.getByRole("dialog", { name: "Cobro" });
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: metodo }).click();
  await dialog.getByRole("button", { name: /^Confirmar/ }).click();
}
