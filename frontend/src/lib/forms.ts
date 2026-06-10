// Conversiones PURAS entre lo que teclea el usuario (pesos, unidades) y lo que
// guarda el modelo (centavos, milésimas). Enteros siempre; testeable en aislamiento.

import { MILESIMAS_POR_UNIDAD } from "./money";

/** Pesos (string del input) → centavos enteros. COP circula en pesos enteros:
 * redondeamos a peso antes de ×100 para no introducir fracciones de centavo. */
export function pesosACentavos(pesos: string | number): number {
  const n = Math.round(Number(pesos || 0));
  return Number.isFinite(n) && n >= 0 ? n * 100 : 0;
}

/** Centavos → valor en pesos para el `value` de un input numérico. */
export function centavosAPesos(centavos: number): number {
  return Math.round(centavos / 100);
}

/** Unidades (string del input) → milésimas enteras (1000 = 1 unidad). */
export function unidadesAMilesimas(unidades: string | number): number {
  const n = Number(unidades || 0);
  if (!Number.isFinite(n) || n < 0) return 0;
  return Math.round(n * MILESIMAS_POR_UNIDAD);
}

/** Milésimas → unidades (número) para mostrar/editar. */
export function milesimasAUnidades(milesimas: number): number {
  return milesimas / MILESIMAS_POR_UNIDAD;
}
