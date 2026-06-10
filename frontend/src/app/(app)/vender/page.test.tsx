import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import VenderPage from "./page";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, apiGet: vi.fn(), apiPost: vi.fn() };
});

import { apiGet, apiPost } from "@/lib/api";

const apiGetMock = vi.mocked(apiGet);
const apiPostMock = vi.mocked(apiPost);

const PRODUCTO = {
  id: 1,
  nombre: "Gaseosa 400ml",
  sku: "G1",
  codigo_barras: null,
  categoria: null,
  precio_venta_centavos: 100000,
  precio_costo_centavos: 50000,
  iva: "tarifa_19" as const,
  unidad: "unidad",
  stock_milesimas: 10000,
  stock_minimo_milesimas: 0,
  margen_centavos: 50000,
  margen_bps: 5000,
  stock_bajo: false,
  activo: true,
};

describe("VenderPage", () => {
  beforeEach(() => {
    apiGetMock.mockReset();
    apiPostMock.mockReset();
    apiGetMock.mockResolvedValue([PRODUCTO]);
  });

  it("agrega un producto y calcula el total con IVA en vivo", async () => {
    const user = userEvent.setup();
    render(<VenderPage />);

    await user.type(screen.getByLabelText("Buscar producto"), "gas");
    const card = await screen.findByText("Gaseosa 400ml");
    await user.click(card);

    // 1 unidad a $1.000 + IVA 19% = $1.190.
    expect(screen.getByTestId("cart-total")).toHaveTextContent("1.190");
  });

  it("cobra y muestra el ticket con el número de factura", async () => {
    apiPostMock.mockResolvedValue({
      id: 7,
      subtotal_centavos: 100000,
      iva_total_centavos: 19000,
      total_centavos: 119000,
      status: "pagada",
      metodo_pago: "efectivo",
      created_at: "2026-06-09T12:00:00",
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
        created_at: "2026-06-09T12:00:00",
      },
    });

    const user = userEvent.setup();
    render(<VenderPage />);

    await user.type(screen.getByLabelText("Buscar producto"), "gas");
    await user.click(await screen.findByText("Gaseosa 400ml"));
    await user.click(screen.getByRole("button", { name: "Cobrar" }));

    const dialog = screen.getByRole("dialog", { name: "Cobro" });
    await user.click(within(dialog).getByRole("button", { name: "Confirmar" }));

    expect(await screen.findByText("POS-000001")).toBeInTheDocument();
    // El payload de cobro no incluye precios.
    expect(JSON.stringify(apiPostMock.mock.calls[0][1])).not.toContain("precio");
  });

  it("muestra el error si no hay caja abierta al cobrar", async () => {
    const { ApiError } = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
    apiPostMock.mockRejectedValue(
      new ApiError(409, "No hay caja abierta — ábrela para empezar a vender"),
    );

    const user = userEvent.setup();
    render(<VenderPage />);

    await user.type(screen.getByLabelText("Buscar producto"), "gas");
    await user.click(await screen.findByText("Gaseosa 400ml"));
    await user.click(screen.getByRole("button", { name: "Cobrar" }));
    const dialog = screen.getByRole("dialog", { name: "Cobro" });
    await user.click(within(dialog).getByRole("button", { name: "Confirmar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("No hay caja abierta");
  });
});
