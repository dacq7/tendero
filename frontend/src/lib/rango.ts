// Lógica PURA de los presets de rango de fechas del dashboard. Testeable.

import type { Granularidad } from "./types";

export type Preset = "hoy" | "7d" | "30d" | "mes" | "ano";

export interface Rango {
  desde: string; // YYYY-MM-DD
  hasta: string;
}

function iso(d: Date): string {
  return d.toISOString().slice(0, 10);
}

/** Calcula el rango [desde, hasta] (hasta inclusivo) para un preset, dado "hoy". */
export function rangoDePreset(preset: Preset, hoy: Date): Rango {
  const hasta = iso(hoy);
  const d = new Date(hoy);
  switch (preset) {
    case "hoy":
      return { desde: hasta, hasta };
    case "7d":
      d.setDate(d.getDate() - 6);
      return { desde: iso(d), hasta };
    case "30d":
      d.setDate(d.getDate() - 29);
      return { desde: iso(d), hasta };
    case "mes":
      return { desde: iso(new Date(hoy.getFullYear(), hoy.getMonth(), 1)), hasta };
    case "ano":
      return { desde: iso(new Date(hoy.getFullYear(), 0, 1)), hasta };
  }
}

/** Granularidad sugerida según el tamaño del rango (días). */
export function granularidadSugerida(desde: string, hasta: string): Granularidad {
  const dias = (Date.parse(hasta) - Date.parse(desde)) / 86_400_000;
  if (dias <= 31) return "dia";
  if (dias <= 120) return "semana";
  if (dias <= 800) return "mes";
  return "ano";
}

export function rangoValido(desde: string, hasta: string): boolean {
  return Boolean(desde) && Boolean(hasta) && Date.parse(desde) <= Date.parse(hasta);
}
