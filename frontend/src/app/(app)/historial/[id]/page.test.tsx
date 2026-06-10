import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import VentaDetallePage from "./page";

vi.mock("next/navigation", () => ({ useParams: () => ({ id: "7" }) }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, apiGet: vi.fn(), apiPost: vi.fn() };
});

import { apiGet } from "@/lib/api";

const apiGetMock = vi.mocked(apiGet);

const SALE = {
  id: 7,
  subtotal_centavos: 100000,
  iva_total_centavos: 19000,
  total_centavos: 119000,
  status: "pagada",
  metodo_pago: "efectivo",
  paid_at: "2026-06-10T12:00:00",
  created_at: "2026-06-10T12:00:00",
  items: [
    {
      id: 1,
      nombre_snapshot: "Gaseosa 400ml",
      sku_snapshot: "G1",
      cantidad_milesimas: 1000,
      precio_unitario_centavos: 100000,
      base_centavos: 100000,
      iva_centavos: 19000,
      total_linea_centavos: 119000,
    },
  ],
  invoice: {
    id: 1,
    sale_id: 7,
    numero_completo: "POS-000001",
    subtotal_centavos: 100000,
    iva_total_centavos: 19000,
    total_centavos: 119000,
    metodo_pago: "efectivo",
    dian_status: "none",
    cufe: null,
    created_at: "2026-06-10T12:00:00",
  },
};

describe("VentaDetallePage", () => {
  beforeEach(() => apiGetMock.mockReset());

  it("muestra las líneas (snapshot), la factura y permite emitir (admin)", async () => {
    apiGetMock.mockImplementation(async (path: string) => {
      if (path === "auth/me") return { id: 1, email: "a@b.co", full_name: "A", role: "admin" };
      return SALE;
    });
    render(<VentaDetallePage />);

    expect(await screen.findByText("Gaseosa 400ml")).toBeInTheDocument();
    expect(screen.getAllByText("POS-000001").length).toBeGreaterThan(0);
    expect(screen.getByText("Sin emitir")).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Emitir a DIAN" })).toBeInTheDocument();
  });

  it("el cajero NO ve el botón de emitir", async () => {
    apiGetMock.mockImplementation(async (path: string) => {
      if (path === "auth/me") return { id: 2, email: "c@b.co", full_name: "C", role: "cajero" };
      return SALE;
    });
    render(<VentaDetallePage />);
    await screen.findByText("Gaseosa 400ml");
    expect(screen.queryByRole("button", { name: "Emitir a DIAN" })).not.toBeInTheDocument();
  });
});
