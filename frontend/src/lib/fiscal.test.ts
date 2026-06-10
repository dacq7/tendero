import { describe, expect, it } from "vitest";

import { dianBadge, puedeEmitir } from "./fiscal";

describe("dianBadge", () => {
  it("mapea cada estado a su etiqueta y tono", () => {
    expect(dianBadge("none")).toEqual({ text: "Sin emitir", tone: "neutral" });
    expect(dianBadge("pending")).toEqual({ text: "Pendiente", tone: "info" });
    expect(dianBadge("accepted")).toEqual({ text: "Aceptada", tone: "ok" });
    expect(dianBadge("rejected")).toEqual({ text: "Rechazada", tone: "error" });
  });
});

describe("puedeEmitir", () => {
  it("permite (re)emitir solo en 'none' y 'rejected'", () => {
    expect(puedeEmitir("none")).toBe(true);
    expect(puedeEmitir("rejected")).toBe(true);
    expect(puedeEmitir("pending")).toBe(false);
    expect(puedeEmitir("accepted")).toBe(false);
  });
});
