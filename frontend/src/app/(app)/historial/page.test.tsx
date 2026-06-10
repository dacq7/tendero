import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import HistorialPage from "./page";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, apiGet: vi.fn(), apiPost: vi.fn() };
});

import { apiGet, apiPost } from "@/lib/api";

const apiGetMock = vi.mocked(apiGet);
const apiPostMock = vi.mocked(apiPost);

const INVOICE = {
  id: 1,
  sale_id: 1,
  numero_completo: "POS-000001",
  subtotal_centavos: 100000,
  iva_total_centavos: 19000,
  total_centavos: 119000,
  metodo_pago: "efectivo",
  dian_status: "none" as const,
  cufe: null,
  created_at: "2026-06-10T12:00:00",
};

function mockApi(role: "admin" | "cajero") {
  apiGetMock.mockImplementation(async (path: string) => {
    if (path.startsWith("invoices")) return [INVOICE];
    return { id: 1, email: "a@b.co", full_name: "A", role };
  });
}

describe("HistorialPage", () => {
  beforeEach(() => {
    apiGetMock.mockReset();
    apiPostMock.mockReset();
  });

  it("muestra el badge DIAN 'Sin emitir'", async () => {
    mockApi("cajero");
    render(<HistorialPage />);
    expect(await screen.findByText("Sin emitir")).toBeInTheDocument();
  });

  it("el cajero NO ve el botón de emitir", async () => {
    mockApi("cajero");
    render(<HistorialPage />);
    await screen.findByText("Sin emitir");
    expect(screen.queryByRole("button", { name: "Emitir a DIAN" })).not.toBeInTheDocument();
  });

  it("el admin emite y la fila pasa a 'Aceptada' con CUFE", async () => {
    mockApi("admin");
    apiPostMock.mockResolvedValue({
      id: 1,
      invoice_id: 1,
      numero_fiscal_completo: "SETP990000001",
      provider: "mock",
      status: "accepted",
      cufe: "abc123",
      motivo_rechazo: null,
      intentos: 1,
    });
    const user = userEvent.setup();
    render(<HistorialPage />);

    await user.click(await screen.findByRole("button", { name: "Emitir a DIAN" }));

    expect(await screen.findByText("Aceptada")).toBeInTheDocument();
    expect(screen.getByText(/CUFE abc123/)).toBeInTheDocument();
  });

  it("muestra siempre el aviso de no-validez fiscal", async () => {
    mockApi("admin");
    render(<HistorialPage />);
    expect(await screen.findByText(/no tienen validez fiscal/)).toBeInTheDocument();
  });
});
