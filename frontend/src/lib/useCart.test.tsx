import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { Product } from "./cart";
import { useCart } from "./useCart";

const PROD: Product = {
  id: 1,
  nombre: "Gaseosa",
  sku: "G1",
  precio_venta_centavos: 100000,
  iva: "tarifa_19",
  unidad: "unidad",
  stock_milesimas: 10000,
};

afterEach(() => window.sessionStorage.clear());

describe("useCart", () => {
  it("agrega y suma en unidades enteras (1000 milésimas)", () => {
    const { result } = renderHook(() => useCart());
    act(() => result.current.add(PROD));
    expect(result.current.cart[0].cantidad_milesimas).toBe(1000);
    act(() => result.current.add(PROD));
    expect(result.current.cart[0].cantidad_milesimas).toBe(2000);
  });

  it("persiste en sessionStorage y se restaura al remontar", () => {
    const primero = renderHook(() => useCart());
    act(() => primero.result.current.add(PROD));
    primero.unmount();
    // Nuevo montaje (simula volver a la pantalla): el carrito sigue ahí.
    const segundo = renderHook(() => useCart());
    expect(segundo.result.current.cart).toHaveLength(1);
    expect(segundo.result.current.cart[0].product.id).toBe(1);
  });

  it("arranca vacío si sessionStorage está corrupto", () => {
    window.sessionStorage.setItem("tendero_cart", "{no-es-json}");
    const { result } = renderHook(() => useCart());
    expect(result.current.cart).toHaveLength(0);
  });

  it("vaciar limpia el carrito", () => {
    const { result } = renderHook(() => useCart());
    act(() => result.current.add(PROD));
    act(() => result.current.vaciar());
    expect(result.current.cart).toHaveLength(0);
  });
});
