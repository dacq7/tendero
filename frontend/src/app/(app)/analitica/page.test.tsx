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

describe("AnaliticaPage", () => {
  beforeEach(() => {
    apiGetMock.mockReset();
    apiGetMock.mockImplementation(async (path: string) => {
      if (path.startsWith("analytics/summary")) return SUMMARY;
      if (path.startsWith("analytics/timeseries"))
        return [{ periodo: "2026-05-01", ventas_centavos: 100000, n_transacciones: 1, margen_centavos: 40000 }];
      if (path.startsWith("analytics/top-products"))
        return [{ product_id: 1, nombre: "Aguardiente", ventas_centavos: 200000000, cantidad_milesimas: 1000, margen_centavos: 50000000 }];
      if (path.startsWith("analytics/by-method"))
        return [{ metodo: "efectivo", ventas_centavos: 300000000, n_transacciones: 800 }];
      return { stock_valorizado_centavos: 88000000000, cogs_periodo_centavos: 250000000, rotacion_bps: 284, n_stock_bajo: 2 };
    });
  });

  it("renderiza los KPIs con cifras y delta vs periodo anterior", async () => {
    render(<AnaliticaPage />);
    // Ventas $5.000.000 y su delta +25.0%.
    expect(await screen.findByText("Ventas")).toBeInTheDocument();
    expect(screen.getByText((t) => t.includes("5.000.000"))).toBeInTheDocument();
    expect(screen.getByText("+25.0%")).toBeInTheDocument();
    expect(screen.getByText("Transacciones")).toBeInTheDocument();
    expect(screen.getByText("1200")).toBeInTheDocument();
  });

  it("muestra el producto top y el panel de inventario", async () => {
    render(<AnaliticaPage />);
    expect(await screen.findByText("Aguardiente")).toBeInTheDocument();
    expect(screen.getByText("Stock valorizado")).toBeInTheDocument();
  });
});
