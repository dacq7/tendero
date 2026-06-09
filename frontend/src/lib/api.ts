const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8020";

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
  } catch {
    throw new ApiError(0, "No se pudo conectar con el servidor. ¿Está encendido?");
  }

  if (!res.ok) {
    const detail =
      res.status === 401
        ? "Correo o contraseña incorrectos."
        : "Algo salió mal al entrar. Intenta de nuevo.";
    throw new ApiError(res.status, detail);
  }

  return (await res.json()) as TokenResponse;
}
