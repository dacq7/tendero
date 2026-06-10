import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Product } from "@/lib/types";

import ProductoForm from "./ProductoForm";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, apiPost: vi.fn(), apiPatch: vi.fn() };
});

import { apiPatch, apiPost } from "@/lib/api";

const apiPostMock = vi.mocked(apiPost);
const apiPatchMock = vi.mocked(apiPatch);

const PRODUCTO: Product = {
  id: 7,
  nombre: "Arroz 1kg",
  sku: "ARZ-1",
  codigo_barras: null,
  categoria: "Abarrotes",
  supplier_id: null,
  precio_venta_centavos: 420000,
  precio_costo_centavos: 300000,
  iva: "exento",
  unidad: "kg",
  stock_milesimas: 25000,
  stock_minimo_milesimas: 3000,
  margen_centavos: 120000,
  margen_bps: 2857,
  stock_bajo: false,
  activo: true,
};

describe("ProductoForm", () => {
  beforeEach(() => {
    apiPostMock.mockReset();
    apiPatchMock.mockReset();
    apiPostMock.mockResolvedValue({ id: 99 });
  });

  it("alta: NO tiene campo de stock libre y el payload no envía stock_milesimas", async () => {
    const user = userEvent.setup();
    render(<ProductoForm proveedores={[]} onDone={vi.fn()} />);

    await user.type(screen.getByLabelText(/Nombre/), "Gaseosa");
    await user.type(screen.getByLabelText(/SKU/), "G-1");
    await user.type(screen.getByLabelText("Precio venta (pesos)"), "2000");
    await user.click(screen.getByRole("button", { name: "Crear producto" }));

    expect(apiPostMock).toHaveBeenCalledWith("products", expect.anything());
    const body = apiPostMock.mock.calls[0][1] as Record<string, unknown>;
    expect(body).not.toHaveProperty("stock_milesimas");
    expect(body.precio_venta_centavos).toBe(200000); // 2000 pesos → centavos
  });

  it("alta: carga inicial opcional se registra como ENTRADA (no como stock)", async () => {
    const user = userEvent.setup();
    render(<ProductoForm proveedores={[]} onDone={vi.fn()} />);

    await user.type(screen.getByLabelText(/Nombre/), "Gaseosa");
    await user.type(screen.getByLabelText(/SKU/), "G-1");
    await user.type(screen.getByLabelText("Cantidad inicial (unidades)"), "10");
    await user.type(screen.getByLabelText("Costo unitario (pesos)"), "1200");
    await user.click(screen.getByRole("button", { name: "Crear producto" }));

    // 1ª llamada crea el producto; 2ª registra la entrada de inventario.
    expect(apiPostMock).toHaveBeenCalledTimes(2);
    const entrada = apiPostMock.mock.calls[1];
    expect(entrada[0]).toBe("inventory/movements");
    expect(entrada[1]).toMatchObject({
      tipo: "entrada",
      cantidad_milesimas: 10000, // 10 unidades
      costo_unitario_centavos: 120000, // 1200 pesos
    });
  });

  it("edición: el stock es de SOLO LECTURA y el PATCH no envía stock_milesimas", async () => {
    apiPatchMock.mockResolvedValue({});
    const user = userEvent.setup();
    render(<ProductoForm producto={PRODUCTO} proveedores={[]} onDone={vi.fn()} />);

    // Stock mostrado como texto de solo lectura (no un input editable).
    expect(screen.getByTestId("stock-readonly")).toBeInTheDocument();
    expect(screen.queryByLabelText(/^Stock actual/)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
    expect(apiPatchMock).toHaveBeenCalledWith("products/7", expect.anything());
    const body = apiPatchMock.mock.calls[0][1] as Record<string, unknown>;
    expect(body).not.toHaveProperty("stock_milesimas");
  });
});
