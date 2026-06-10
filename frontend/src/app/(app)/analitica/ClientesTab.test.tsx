import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ClientesTab from "./ClientesTab";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, apiGet: vi.fn() };
});

import { apiGet } from "@/lib/api";

const apiGetMock = vi.mocked(apiGet);

const SEGMENTS = {
  identificado: { ventas_centavos: 600000, n_transacciones: 3, ticket_promedio_centavos: 200000 },
  anonimo: { ventas_centavos: 100000, n_transacciones: 1, ticket_promedio_centavos: 100000 },
};

// Dos clientes DISTINTOS que comparten los mismos últimos 4 dígitos enmascarados.
// Antes esto colisionaba como key de React (warning + filas perdidas).
const TOP_DOC_COLISION = [
  { customer_doc: "···4567", nombre: "Ana", gasto_centavos: 400000, n_compras: 2, ticket_promedio_centavos: 200000, ultima: "2026-05-10" },
  { customer_doc: "···4567", nombre: "Beto", gasto_centavos: 200000, n_compras: 1, ticket_promedio_centavos: 200000, ultima: "2026-05-09" },
];

describe("ClientesTab", () => {
  const rango = { desde: "2026-05-01", hasta: "2026-05-30" };
  let errorSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    apiGetMock.mockReset();
    apiGetMock.mockImplementation(async (path: string) => {
      if (path.startsWith("analytics/customers/top")) return TOP_DOC_COLISION;
      if (path.startsWith("analytics/customers/segments")) return SEGMENTS;
      return [];
    });
  });

  afterEach(() => {
    errorSpy.mockRestore();
  });

  it("renderiza AMBAS filas cuando dos clientes comparten el documento enmascarado", async () => {
    render(<ClientesTab rango={rango} />);
    // Las dos filas se renderizan pese a compartir customer_doc.
    expect(await screen.findByText("Ana")).toBeInTheDocument();
    expect(screen.getByText("Beto")).toBeInTheDocument();
  });

  it("no emite warning de key duplicada de React", async () => {
    render(<ClientesTab rango={rango} />);
    await screen.findByText("Ana");
    const huboKeyDuplicada = errorSpy.mock.calls.some((args) =>
      args.some((a) => typeof a === "string" && a.includes("same key")),
    );
    expect(huboKeyDuplicada).toBe(false);
  });
});
