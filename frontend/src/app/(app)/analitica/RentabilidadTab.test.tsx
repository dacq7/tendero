import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import RentabilidadTab from "./RentabilidadTab";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, apiGet: vi.fn() };
});

import { apiGet } from "@/lib/api";

const apiGetMock = vi.mocked(apiGet);

const PRODUCTOS = [
  { product_id: 1, nombre: "Aguardiente", ventas_centavos: 200000000, margen_centavos: 50000000, margen_bps: 3076, contribucion_bps: 1667 },
  { product_id: 2, nombre: "Bombón", ventas_centavos: 50000, margen_centavos: 7500, margen_bps: 1500, contribucion_bps: 10 },
];

describe("RentabilidadTab", () => {
  beforeEach(() => {
    apiGetMock.mockReset();
    apiGetMock.mockImplementation(async (path: string) => {
      if (path.startsWith("analytics/profit-products")) return PRODUCTOS;
      if (path.startsWith("analytics/profit-categories"))
        return [{ categoria: "Licores", ventas_centavos: 200000000, margen_centavos: 50000000, margen_bps: 3076, contribucion_bps: 9000 }];
      if (path.startsWith("analytics/profit-matrix"))
        return {
          items: [
            { product_id: 1, nombre: "Aguardiente", volumen_milesimas: 2000, ventas_centavos: 200000000, margen_bps: 3076, cuadrante: "estrella" },
            { product_id: 2, nombre: "Bombón", volumen_milesimas: 500, ventas_centavos: 50000, margen_bps: 1500, cuadrante: "perro" },
          ],
          umbral_volumen_milesimas: 1250,
          umbral_margen_bps: 2288,
        };
      return [];
    });
  });

  const rango = { desde: "2026-05-01", hasta: "2026-05-30" };

  it("muestra la matriz estrella/perro y su leyenda de cuadrantes", async () => {
    render(<RentabilidadTab rango={rango} />);
    expect(
      await screen.findByText((t) => t.includes("Matriz volumen × margen")),
    ).toBeInTheDocument();
    // La leyenda nombra los cuadrantes (estrella y perro entre ellos).
    expect(screen.getByText((t) => t.startsWith("Estrella"))).toBeInTheDocument();
    expect(screen.getByText((t) => t.startsWith("Perro"))).toBeInTheDocument();
  });

  it("lista la rentabilidad por producto con su contribución", async () => {
    render(<RentabilidadTab rango={rango} />);
    // "Aguardiente" aparece en la tabla de rentabilidad por producto.
    expect(await screen.findAllByText("Aguardiente")).not.toHaveLength(0);
    // Margen formateado ($500.000) y contribución 16,7%.
    expect(screen.getByText((t) => t.includes("16,7%"))).toBeInTheDocument();
  });
});
