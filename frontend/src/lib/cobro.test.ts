import { describe, expect, it } from "vitest";

import { isWompiMethod, phaseForPaymentStatus } from "./cobro";

describe("isWompiMethod", () => {
  it("tarjeta, pse y nequi son Wompi", () => {
    expect(isWompiMethod("tarjeta")).toBe(true);
    expect(isWompiMethod("pse")).toBe(true);
    expect(isWompiMethod("nequi")).toBe(true);
  });

  it("efectivo y transferencia son cobro local", () => {
    expect(isWompiMethod("efectivo")).toBe(false);
    expect(isWompiMethod("transferencia")).toBe(false);
  });
});

describe("phaseForPaymentStatus", () => {
  it("approved → ticket, pending → procesando, declined → rechazado", () => {
    expect(phaseForPaymentStatus("approved")).toBe("ticket");
    expect(phaseForPaymentStatus("pending")).toBe("procesando");
    expect(phaseForPaymentStatus("declined")).toBe("rechazado");
    expect(phaseForPaymentStatus("error")).toBe("rechazado");
    expect(phaseForPaymentStatus("voided")).toBe("rechazado");
  });
});
