import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api";
import LoginPage from "./page";

// Mockeamos solo `login`; conservamos `ApiError` real para probar el manejo
// de errores de la API.
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, login: vi.fn() };
});

import { login } from "@/lib/api";

const loginMock = vi.mocked(login);

// Credenciales ficticias: `login` está mockeado, nunca llegan a una API real.
async function fillCredentials(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("Correo"), "tendero@tienda.co");
  await user.type(screen.getByLabelText("Contraseña"), "Secreta123");
}

describe("LoginPage", () => {
  beforeEach(() => {
    loginMock.mockReset();
  });

  it("renderiza el formulario de entrada", () => {
    render(<LoginPage />);
    expect(screen.getByRole("heading", { name: "Entrar" })).toBeInTheDocument();
    expect(screen.getByLabelText("Correo")).toBeInTheDocument();
    expect(screen.getByLabelText("Contraseña")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Entrar" })).toBeInTheDocument();
  });

  it("muestra el mensaje de error cuando las credenciales son inválidas", async () => {
    loginMock.mockRejectedValueOnce(new ApiError(401, "Correo o contraseña incorrectos."));
    const user = userEvent.setup();
    render(<LoginPage />);

    await fillCredentials(user);
    await user.click(screen.getByRole("button", { name: "Entrar" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Correo o contraseña incorrectos.");
  });

  it("muestra el estado de carga mientras la petición está en curso", async () => {
    // Promesa que no resolvemos: deja el formulario en estado de carga.
    loginMock.mockReturnValueOnce(new Promise(() => {}));
    const user = userEvent.setup();
    render(<LoginPage />);

    await fillCredentials(user);
    await user.click(screen.getByRole("button", { name: "Entrar" }));

    const button = screen.getByRole("button", { name: "Entrando…" });
    expect(button).toBeDisabled();
  });

  it("muestra la confirmación cuando el login responde correctamente", async () => {
    loginMock.mockResolvedValueOnce({
      access_token: "a",
      refresh_token: "r",
      token_type: "bearer",
    });
    const user = userEvent.setup();
    render(<LoginPage />);

    await fillCredentials(user);
    await user.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByText("Sesión iniciada")).toBeInTheDocument();
  });
});
