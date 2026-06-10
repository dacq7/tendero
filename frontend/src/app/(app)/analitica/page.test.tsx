import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AnaliticaPage from "./page";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, apiGet: vi.fn() };
});

import { apiGet } from "@/lib/api";

const apiGetMock = vi.mocked(apiGet);

const SUMMARY = {
  desde: "2026-05-01",
  hasta: "2026-05-30",
  ventas_centavos: 500000000,
  subtotal_centavos: 420000000,
  iva_centavos: 80000000,
  cogs_centavos: 250000000,
  n_transacciones: 1200,
  ticket_promedio_centavos: 416667,
  margen_centavos: 170000000,
  margen_bps: 4047,
  comparativa: {
    ventas_centavos: 400000000,
    n_transacciones: 1000,
    ticket_promedio_centavos: 400000,
    margen_centavos: 150000000,
    delta_ventas_bps: 2500,
    delta_transacciones_bps: 2000,
    delta_ticket_bps: 416,
    delta_margen_bps: 1333,
  },
};

// Respuestas por endpoint para que cualquier pestaña que se monte tenga datos.
function respuesta(path: string): unknown {
  if (path === "auth/me") return { id: 1, email: "a@a.co", full_name: "Admin", role: "admin" };
  if (path.startsWith("analytics/summary")) return SUMMARY;
  if (path.startsWith("analytics/timeseries"))
    return [{ periodo: "2026-05-01", ventas_centavos: 100000, n_transacciones: 1, margen_centavos: 40000 }];
  if (path.startsWith("analytics/top-products"))
    return [{ product_id: 1, nombre: "Aguardiente", ventas_centavos: 200000000, cantidad_milesimas: 1000, margen_centavos: 50000000 }];
  if (path.startsWith("analytics/by-method"))
    return [{ metodo: "efectivo", ventas_centavos: 300000000, n_transacciones: 800 }];
  if (path.startsWith("analytics/profit-products"))
    return [{ product_id: 1, nombre: "Aguardiente", ventas_centavos: 200000000, margen_centavos: 50000000, margen_bps: 3076, contribucion_bps: 1667 }];
  if (path.startsWith("analytics/profit-categories"))
    return [{ categoria: "Licores", ventas_centavos: 200000000, margen_centavos: 50000000, margen_bps: 3076, contribucion_bps: 4000 }];
  if (path.startsWith("analytics/profit-matrix"))
    return {
      items: [{ product_id: 1, nombre: "Aguardiente", volumen_milesimas: 2000, ventas_centavos: 200000000, margen_bps: 3076, cuadrante: "estrella" }],
      umbral_volumen_milesimas: 1500,
      umbral_margen_bps: 2000,
    };
  return [];
}

describe("AnaliticaPage (pestañas)", () => {
  beforeEach(() => {
    apiGetMock.mockReset();
    apiGetMock.mockImplementation(async (path: string) => respuesta(path));
  });

  it("muestra las pestañas de navegación", async () => {
    render(<AnaliticaPage />);
    expect(await screen.findByRole("button", { name: "Resumen" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Rentabilidad" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Inventario" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tendencias" })).toBeInTheDocument();
  });

  it("renderiza el Resumen por defecto con KPIs y delta vs periodo anterior", async () => {
    render(<AnaliticaPage />);
    expect(await screen.findByText("Ventas")).toBeInTheDocument();
    expect(screen.getByText((t) => t.includes("5.000.000"))).toBeInTheDocument();
    expect(screen.getByText("+25.0%")).toBeInTheDocument();
    expect(screen.getByText("1200")).toBeInTheDocument();
  });
});
