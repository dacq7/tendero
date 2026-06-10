// Dinero en centavos COP enteros y cantidades en milésimas (1000 = 1 unidad),
// igual que el backend. El cálculo de IVA refleja services/sale_pricing.py para
// dar feedback en vivo; la VERDAD la fija el backend al cobrar.

export type IvaRate = "exento" | "tarifa_0" | "tarifa_5" | "tarifa_19";

// Milésimas por unidad: 1000 = 1 unidad / 1 kg. El control de cantidad de la UI
// suma/resta en UNIDADES (este paso), no en milésimas.
export const MILESIMAS_POR_UNIDAD = 1000;

export const IVA_BPS: Record<IvaRate, number> = {
  exento: 0,
  tarifa_0: 0,
  tarifa_5: 500,
  tarifa_19: 1900,
};

/** División entera con redondeo half-up determinista (igual que money.py). */
export function roundHalfUp(numerador: number, denominador: number): number {
  return Math.floor((numerador + Math.floor(denominador / 2)) / denominador);
}

/** Formatea centavos a pesos COP, p. ej. 119000 → "$1.190". */
export function formatCOP(centavos: number): string {
  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    maximumFractionDigits: 0,
  }).format(Math.round(centavos / 100));
}

/** Formatea milésimas a cantidad legible, p. ej. 500 → "0,5", 3000 → "3". */
export function formatCantidad(milesimas: number): string {
  return new Intl.NumberFormat("es-CO", { maximumFractionDigits: 3 }).format(
    milesimas / 1000,
  );
}
