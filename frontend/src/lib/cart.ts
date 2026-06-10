// Lógica PURA del carrito de venta. Sin React: testeable en aislamiento.
// El precio del producto es la BASE sin IVA; el IVA se suma encima (decisión de
// Fase 2). Refleja el backend para el feedback en vivo del mostrador.

import { IVA_BPS, type IvaRate, roundHalfUp } from "./money";

export interface Product {
  id: number;
  nombre: string;
  sku: string;
  precio_venta_centavos: number;
  iva: IvaRate;
  unidad: string;
  stock_milesimas: number;
}

export interface CartLine {
  product: Product;
  cantidad_milesimas: number;
}

export interface LineTotals {
  base_centavos: number;
  iva_centavos: number;
  total_linea_centavos: number;
}

export interface CartTotals {
  subtotal_centavos: number;
  iva_total_centavos: number;
  total_centavos: number;
}

export function lineTotals(line: CartLine): LineTotals {
  const base = roundHalfUp(
    line.product.precio_venta_centavos * line.cantidad_milesimas,
    1000,
  );
  const iva = roundHalfUp(base * IVA_BPS[line.product.iva], 10000);
  return { base_centavos: base, iva_centavos: iva, total_linea_centavos: base + iva };
}

export function cartTotals(lines: CartLine[]): CartTotals {
  return lines.reduce<CartTotals>(
    (acc, line) => {
      const t = lineTotals(line);
      return {
        subtotal_centavos: acc.subtotal_centavos + t.base_centavos,
        iva_total_centavos: acc.iva_total_centavos + t.iva_centavos,
        total_centavos: acc.total_centavos + t.total_linea_centavos,
      };
    },
    { subtotal_centavos: 0, iva_total_centavos: 0, total_centavos: 0 },
  );
}

/** Agrega un producto (o suma 1000 milésimas = 1 unidad si ya está). */
export function addToCart(lines: CartLine[], product: Product): CartLine[] {
  const existing = lines.find((l) => l.product.id === product.id);
  if (existing) {
    return lines.map((l) =>
      l.product.id === product.id
        ? { ...l, cantidad_milesimas: l.cantidad_milesimas + 1000 }
        : l,
    );
  }
  return [...lines, { product, cantidad_milesimas: 1000 }];
}

export function setCantidad(
  lines: CartLine[],
  productId: number,
  cantidad_milesimas: number,
): CartLine[] {
  if (cantidad_milesimas <= 0) {
    return lines.filter((l) => l.product.id !== productId);
  }
  return lines.map((l) =>
    l.product.id === productId ? { ...l, cantidad_milesimas } : l,
  );
}

export function removeFromCart(lines: CartLine[], productId: number): CartLine[] {
  return lines.filter((l) => l.product.id !== productId);
}

/** Payload para POST /sales: el cliente NUNCA envía precios. */
export function toSalePayload(lines: CartLine[], metodo_pago: string) {
  return {
    metodo_pago,
    lineas: lines.map((l) => ({
      product_id: l.product.id,
      cantidad_milesimas: l.cantidad_milesimas,
    })),
  };
}
