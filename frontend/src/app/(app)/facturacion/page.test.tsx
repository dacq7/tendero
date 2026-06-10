import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import FacturacionPage from "./page";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, apiGet: vi.fn(), apiPost: vi.fn(), apiPatch: vi.fn() };
});

import { apiGet, apiPost } from "@/lib/api";

const apiGetMock = vi.mocked(apiGet);
const apiPostMock = vi.mocked(apiPost);

const RES = {
  id: 1,
  numero_resolucion: "DEMO-1",
  prefijo: "SETP",
  numero_desde: 990000001,
  numero_hasta: 995000000,
  last_numero: 990000010,
  vigencia_desde: "2025-01-01",
  vigencia_hasta: "2030-12-31",
  rut_nit: "900000000-0",
  responsabilidad: "52",
  activa: true,
  created_at: "2026-01-01",
};

describe("FacturacionPage", () => {
  beforeEach(() => {
    apiGetMock.mockReset();
    apiPostMock.mockReset();
    apiGetMock.mockResolvedValue([RES]);
    apiPostMock.mockResolvedValue({});
  });

  it("lista las resoluciones y marca la activa", async () => {
    render(<FacturacionPage />);
    expect(await screen.findByText(/DEMO-1/)).toBeInTheDocument();
    expect(screen.getByText("activa")).toBeInTheDocument();
  });

  it("crea una resolución (y la activa)", async () => {
    const user = userEvent.setup();
    render(<FacturacionPage />);
    await screen.findByText(/DEMO-1/);

    await user.type(screen.getByLabelText("Número de resolución (DIAN)"), "RES-2");
    await user.type(screen.getByLabelText("Prefijo"), "POS");
    await user.type(screen.getByLabelText("RUT / NIT"), "900000000-0");
    await user.clear(screen.getByLabelText("Hasta"));
    await user.type(screen.getByLabelText("Hasta"), "2000");
    await user.type(screen.getByLabelText("Vigencia desde"), "2026-01-01");
    await user.type(screen.getByLabelText("Vigencia hasta"), "2030-12-31");
    await user.click(screen.getByRole("button", { name: "Crear y activar" }));

    expect(apiPostMock).toHaveBeenCalledWith("fiscal/resolutions", expect.objectContaining({
      numero_resolucion: "RES-2",
      prefijo: "POS",
      activa: true,
    }));
  });

  it("muestra 'solo administradores' si la API responde 403", async () => {
    const { ApiError } = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
    apiGetMock.mockRejectedValue(new ApiError(403, "prohibido"));
    render(<FacturacionPage />);
    expect(await screen.findByText(/solo para administradores/)).toBeInTheDocument();
  });
});
