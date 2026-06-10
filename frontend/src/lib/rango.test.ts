import { describe, expect, it } from "vitest";

import { granularidadSugerida, rangoDePreset, rangoValido } from "./rango";

const HOY = new Date(2026, 5, 15); // 15 jun 2026 (local)

describe("rangoDePreset", () => {
  it("hoy → mismo día", () => {
    expect(rangoDePreset("hoy", HOY)).toEqual({ desde: "2026-06-15", hasta: "2026-06-15" });
  });
  it("7d → 7 días inclusivos", () => {
    expect(rangoDePreset("7d", HOY)).toEqual({ desde: "2026-06-09", hasta: "2026-06-15" });
  });
  it("30d → 30 días inclusivos", () => {
    expect(rangoDePreset("30d", HOY)).toEqual({ desde: "2026-05-17", hasta: "2026-06-15" });
  });
  it("mes → desde el 1º del mes", () => {
    expect(rangoDePreset("mes", HOY).desde).toBe("2026-06-01");
  });
  it("ano → desde el 1 de enero", () => {
    expect(rangoDePreset("ano", HOY).desde).toBe("2026-01-01");
  });
});

describe("granularidadSugerida", () => {
  it("sugiere día/semana/mes/año según el tamaño", () => {
    expect(granularidadSugerida("2026-06-01", "2026-06-15")).toBe("dia");
    expect(granularidadSugerida("2026-04-01", "2026-06-15")).toBe("semana");
    expect(granularidadSugerida("2025-06-01", "2026-06-15")).toBe("mes");
    expect(granularidadSugerida("2020-01-01", "2026-06-15")).toBe("ano");
  });
});

describe("rangoValido", () => {
  it("rechaza desde > hasta", () => {
    expect(rangoValido("2026-06-15", "2026-06-01")).toBe(false);
    expect(rangoValido("2026-06-01", "2026-06-15")).toBe(true);
  });
});
