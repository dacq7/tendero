import { describe, expect, it } from "vitest";

import { centavosAPesos, milesimasAUnidades, pesosACentavos, unidadesAMilesimas } from "./forms";

describe("pesos ↔ centavos", () => {
  it("pesos a centavos (peso entero × 100)", () => {
    expect(pesosACentavos("2000")).toBe(200000);
    expect(pesosACentavos(0)).toBe(0);
    expect(pesosACentavos("")).toBe(0);
  });
  it("ignora valores inválidos o negativos", () => {
    expect(pesosACentavos("abc")).toBe(0);
    expect(pesosACentavos("-5")).toBe(0);
  });
  it("centavos a pesos", () => {
    expect(centavosAPesos(200000)).toBe(2000);
  });
});

describe("unidades ↔ milésimas", () => {
  it("unidades enteras a milésimas", () => {
    expect(unidadesAMilesimas("1")).toBe(1000);
    expect(unidadesAMilesimas("3")).toBe(3000);
  });
  it("soporta fracciones (granel)", () => {
    expect(unidadesAMilesimas("0.5")).toBe(500);
    expect(unidadesAMilesimas("1.25")).toBe(1250);
  });
  it("ignora inválidos", () => {
    expect(unidadesAMilesimas("x")).toBe(0);
    expect(unidadesAMilesimas("-2")).toBe(0);
  });
  it("milésimas a unidades", () => {
    expect(milesimasAUnidades(3000)).toBe(3);
    expect(milesimasAUnidades(500)).toBe(0.5);
  });
});
