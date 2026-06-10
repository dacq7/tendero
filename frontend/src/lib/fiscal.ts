// Lógica PURA de presentación del estado DIAN. Sin React: testeable.

import type { DianStatus } from "./types";

export type DianTone = "neutral" | "info" | "ok" | "error";

interface DianBadge {
  text: string;
  tone: DianTone;
}

// Texto en la voz de la interfaz (no códigos). NO promete validez fiscal.
const BADGES: Record<DianStatus, DianBadge> = {
  none: { text: "Sin emitir", tone: "neutral" },
  pending: { text: "Pendiente", tone: "info" },
  accepted: { text: "Aceptada", tone: "ok" },
  rejected: { text: "Rechazada", tone: "error" },
};

export function dianBadge(status: DianStatus): DianBadge {
  return BADGES[status] ?? BADGES.none;
}

// El admin puede (re)emitir cuando aún no se emitió o fue rechazada.
export function puedeEmitir(status: DianStatus): boolean {
  return status === "none" || status === "rejected";
}
