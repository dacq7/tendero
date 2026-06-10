import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CajaPage from "./page";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, apiGet: vi.fn(), apiPost: vi.fn() };
});

import { apiGet } from "@/lib/api";

const apiGetMock = vi.mocked(apiGet);

const SESSION = {
  id: 5,
  user_id: 1,
  status: "abierta" as const,
  monto_inicial_centavos: 10000000, // $100.000
  abierta_at: "2026-06-10T08:00:00",
  cerrada_at: null,
  efectivo_contado_centavos: null,
  efectivo_esperado_centavos: null,
  diferencia_centavos: null,
};

describe("CajaPage", () => {
  beforeEach(() => {
    apiGetMock.mockReset();
  });

  it("refleja el resumen del turno: total, por método, nº ventas y esperado (bug #3)", async () => {
    apiGetMock.mockImplementation(async (path: string) => {
      if (path === "cash/sessions/current") return SESSION;
      if (path === "cash/sessions/5")
        return { ...SESSION, totales_por_metodo: { efectivo: 30000000, tarjeta: 20000000 } };
      if (path.startsWith("sales?cash_session_id")) return [{ id: 1 }, { id: 2 }]; // 2 ventas
      return null;
    });

    render(<CajaPage />);

    // Vendido en el turno = 30.000.000 + 20.000.000 = $500.000.
    expect(await screen.findByText((t) => t.includes("500.000"))).toBeInTheDocument();
    // Transacciones del turno.
    expect(screen.getByTestId("n-tx")).toHaveTextContent("2");
    // Esperado en efectivo = inicial 100.000 + efectivo 300.000 = $400.000.
    expect(screen.getByTestId("esperado-efectivo")).toHaveTextContent("400.000");
    // Desglose por método visible.
    expect(screen.getByText("Tarjeta")).toBeInTheDocument();
  });

  it("muestra el formulario de apertura cuando no hay caja", async () => {
    apiGetMock.mockRejectedValue(new Error("409"));
    render(<CajaPage />);
    expect(await screen.findByText(/No hay caja abierta/)).toBeInTheDocument();
  });
});
