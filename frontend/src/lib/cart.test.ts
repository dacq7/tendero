import { describe, expect, it } from "vitest";

import {
  addToCart,
  cartTotals,
  type CartLine,
  lineTotals,
  type Product,
  removeFromCart,
  setCantidad,
  toSalePayload,
} from "./cart";

function product(over: Partial<Product> = {}): Product {
  return {
    id: 1,
    nombre: "Gaseosa",
    sku: "G1",
    precio_venta_centavos: 100000,
    iva: "tarifa_19",
    unidad: "unidad",
    stock_milesimas: 10000,
    ...over,
  };
}

describe("lineTotals", () => {
  it("calcula base + IVA 19% para 3 unidades", () => {
    const line: CartLine = { product: product(), cantidad_milesimas: 3000 };
    expect(lineTotals(line)).toEqual({
      base_centavos: 300000,
      iva_centavos: 57000,
      total_linea_centavos: 357000,
    });
  });

  it("exento no causa IVA", () => {
    const line: CartLine = {
      product: product({ iva: "exento" }),
      cantidad_milesimas: 1000,
    };
    expect(lineTotals(line).iva_centavos).toBe(0);
  });

  it("soporta granel (milésimas)", () => {
    const line: CartLine = {
      product: product({ precio_venta_centavos: 200000 }),
      cantidad_milesimas: 500, // 0,5 kg
    };
    expect(lineTotals(line).base_centavos).toBe(100000);
  });
});

describe("cartTotals", () => {
  it("suma líneas con IVA mixto sin descuadre", () => {
    const lines: CartLine[] = [
      { product: product({ id: 1, iva: "tarifa_19" }), cantidad_milesimas: 1000 },
      {
        product: product({ id: 2, iva: "exento", precio_venta_centavos: 200000 }),
        cantidad_milesimas: 1000,
      },
    ];
    const t = cartTotals(lines);
    expect(t.subtotal_centavos).toBe(300000);
    expect(t.iva_total_centavos).toBe(19000);
    expect(t.total_centavos).toBe(319000);
  });

  it("carrito vacío suma cero", () => {
    expect(cartTotals([])).toEqual({
      subtotal_centavos: 0,
      iva_total_centavos: 0,
      total_centavos: 0,
    });
  });
});

describe("mutaciones del carrito", () => {
  it("addToCart agrega y luego suma una unidad", () => {
    let lines = addToCart([], product({ id: 5 }));
    expect(lines).toHaveLength(1);
    expect(lines[0].cantidad_milesimas).toBe(1000);
    lines = addToCart(lines, product({ id: 5 }));
    expect(lines).toHaveLength(1);
    expect(lines[0].cantidad_milesimas).toBe(2000);
  });

  it("setCantidad a 0 elimina la línea", () => {
    const lines: CartLine[] = [{ product: product({ id: 7 }), cantidad_milesimas: 1000 }];
    expect(setCantidad(lines, 7, 0)).toHaveLength(0);
    expect(setCantidad(lines, 7, 5000)[0].cantidad_milesimas).toBe(5000);
  });

  it("removeFromCart quita la línea", () => {
    const lines: CartLine[] = [{ product: product({ id: 9 }), cantidad_milesimas: 1000 }];
    expect(removeFromCart(lines, 9)).toHaveLength(0);
  });
});

describe("toSalePayload", () => {
  it("NO envía precios: solo product_id, cantidad y método", () => {
    const lines: CartLine[] = [{ product: product({ id: 3 }), cantidad_milesimas: 2000 }];
    const payload = toSalePayload(lines, "efectivo");
    expect(payload).toEqual({
      metodo_pago: "efectivo",
      lineas: [{ product_id: 3, cantidad_milesimas: 2000 }],
    });
    expect(JSON.stringify(payload)).not.toContain("precio");
  });
});
