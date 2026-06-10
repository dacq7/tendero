// Lógica PURA del cobro asíncrono (Wompi). Sin React: testeable en aislamiento.

import type { PaymentStatus } from "./types";
import { WOMPI_METHODS } from "./types";

/** ¿El método se cobra por Wompi (asíncrono) o es cobro local (síncrono)? */
export function isWompiMethod(metodo: string): boolean {
  return WOMPI_METHODS.has(metodo);
}

export type CobroPhase = "vender" | "cobrando" | "procesando" | "ticket" | "rechazado";

/** Mapea el estado del pago a la fase de la pantalla. */
export function phaseForPaymentStatus(status: PaymentStatus): CobroPhase {
  if (status === "approved") return "ticket";
  if (status === "pending") return "procesando";
  return "rechazado"; // declined | error | voided
}
