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

  it("cobro Wompi: tarjeta → procesando → simular aprobar → ticket", async () => {
    const ventaPendiente = {
      id: 7,
      subtotal_centavos: 100000,
      iva_total_centavos: 19000,
      total_centavos: 119000,
      status: "pendiente_pago",
      metodo_pago: "tarjeta",
      paid_at: null,
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
      invoice: null,
    };
    const ventaPagada = {
      ...ventaPendiente,
      status: "pagada",
      invoice: {
        id: 1,
        sale_id: 7,
        numero_completo: "POS-000007",
        subtotal_centavos: 100000,
        iva_total_centavos: 19000,
        total_centavos: 119000,
        metodo_pago: "tarjeta",
        dian_status: "none",
        created_at: "2026-06-10T12:00:00",
      },
    };
    apiPostMock.mockImplementation(async (path: string) => {
      if (path === "sales") return ventaPendiente;
      if (path === "payments")
        return { id: 99, sale_id: 7, provider: "mock", metodo: "tarjeta", status: "pending", monto_centavos: 119000, referencia: "SALE-000007", wompi_transaction_id: "mock-tx-1" };
      return { ok: true }; // simulate
    });
    apiGetMock.mockImplementation(async (path: string) => {
      if (path.startsWith("sales/")) return ventaPagada;
      return [PRODUCTO]; // búsqueda de productos
    });

    const user = userEvent.setup();
    render(<VenderPage />);

    await user.type(screen.getByLabelText("Buscar producto"), "gas");
    await user.click(await screen.findByText("Gaseosa 400ml"));
    await user.click(screen.getByRole("button", { name: "Cobrar" }));

    const dialog = screen.getByRole("dialog", { name: "Cobro" });
    await user.click(within(dialog).getByRole("button", { name: "Tarjeta" }));
    await user.click(within(dialog).getByRole("button", { name: "Confirmar" }));

    // Estado asíncrono: pantalla "Procesando pago" con simulación (mock).
    expect(await screen.findByText("Procesando pago")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Aprobar" }));

    // Confirmado: ticket con el número de factura real.
    expect(await screen.findByText("POS-000007")).toBeInTheDocument();
  });

  it("cobro Wompi rechazado muestra el mensaje de rechazo", async () => {
    apiPostMock.mockImplementation(async (path: string) => {
      if (path === "sales")
        return { id: 8, subtotal_centavos: 100000, iva_total_centavos: 19000, total_centavos: 119000, status: "pendiente_pago", metodo_pago: "nequi", paid_at: null, created_at: "x", items: [], invoice: null };
      if (path === "payments")
        return { id: 100, sale_id: 8, provider: "mock", metodo: "nequi", status: "pending", monto_centavos: 119000, referencia: "SALE-000008", wompi_transaction_id: "mock-tx-2" };
      return { ok: true };
    });

    const user = userEvent.setup();
    render(<VenderPage />);

    await user.type(screen.getByLabelText("Buscar producto"), "gas");
    await user.click(await screen.findByText("Gaseosa 400ml"));
    await user.click(screen.getByRole("button", { name: "Cobrar" }));
    const dialog = screen.getByRole("dialog", { name: "Cobro" });
    await user.click(within(dialog).getByRole("button", { name: "Nequi" }));
    await user.click(within(dialog).getByRole("button", { name: "Confirmar" }));

    await user.click(await screen.findByRole("button", { name: "Rechazar" }));
    expect(await screen.findByText("Pago rechazado")).toBeInTheDocument();
  });

  it("muestra la grilla de productos por defecto, sin buscar", async () => {
    render(<VenderPage />);
    // Sin escribir nada, la grilla "Productos" ya ofrece toques rápidos.
    expect(await screen.findByText("Productos")).toBeInTheDocument();
    expect(screen.getByText("Gaseosa 400ml")).toBeInTheDocument();
  });

  it("el control de cantidad sube en UNIDADES enteras (bug #1)", async () => {
    const user = userEvent.setup();
    render(<VenderPage />);
    await user.click(await screen.findByText("Gaseosa 400ml")); // 1 unidad
    const qty = screen.getByTestId("qty-1") as HTMLInputElement;
    expect(qty.value).toBe("1");
    await user.click(screen.getByRole("button", { name: "Sumar Gaseosa 400ml" }));
    await user.click(screen.getByRole("button", { name: "Sumar Gaseosa 400ml" }));
    expect(qty.value).toBe("3"); // 1 → 2 → 3 unidades (no decimales)
    // 3 unidades a $1.000 + IVA = $3.570.
    expect(screen.getByTestId("cart-total")).toHaveTextContent("3.570");
  });

  it("el carrito sobrevive a desmontar y volver (bug #2)", async () => {
    const user = userEvent.setup();
    const vista = render(<VenderPage />);
    await user.click(await screen.findByText("Gaseosa 400ml"));
    expect(screen.getByTestId("cart-total")).toHaveTextContent("1.190");
    vista.unmount(); // navegar a otra sección
    render(<VenderPage />); // volver a Vender
    // El carrito persiste (sessionStorage): el total sigue ahí.
    expect(await screen.findByTestId("cart-total")).toHaveTextContent("1.190");
  });
});
