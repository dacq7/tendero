import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Product } from "@/lib/types";

import MovimientoForm from "./MovimientoForm";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, apiPost: vi.fn() };
});

import { apiPost } from "@/lib/api";

const apiPostMock = vi.mocked(apiPost);

const PRODUCTO = { id: 3 } as Product;

describe("MovimientoForm", () => {
  beforeEach(() => {
    apiPostMock.mockReset();
    apiPostMock.mockResolvedValue({});
  });

  it("merma: convierte unidades→milésimas (3 → 3000)", async () => {
    const user = userEvent.setup();
    render(<MovimientoForm product={PRODUCTO} onDone={vi.fn()} />);
    await user.type(screen.getByLabelText("Cantidad del movimiento"), "3");
    await user.click(screen.getByRole("button", { name: "Registrar movimiento" }));
    expect(apiPostMock).toHaveBeenCalledWith("inventory/movements", {
      product_id: 3,
      tipo: "merma",
      cantidad_milesimas: 3000,
      motivo: null,
    });
  });

  it("ajuste: envía el stock objetivo en milésimas", async () => {
    const user = userEvent.setup();
    render(<MovimientoForm product={PRODUCTO} onDone={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "ajuste" }));
    await user.type(screen.getByLabelText("Cantidad del movimiento"), "5");
    await user.click(screen.getByRole("button", { name: "Registrar movimiento" }));
    expect(apiPostMock.mock.calls[0][1]).toMatchObject({
      tipo: "ajuste",
      cantidad_milesimas: 5000,
    });
  });

  it("rechaza cantidad cero sin llamar a la API", async () => {
    const user = userEvent.setup();
    render(<MovimientoForm product={PRODUCTO} onDone={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Registrar movimiento" }));
    expect(apiPostMock).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("mayor que cero");
  });
});
