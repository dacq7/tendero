// Route Handler de sesión (BFF). POST = login, DELETE = logout.
// Llama al backend server-side y guarda los JWT en cookies httpOnly.

import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import {
  ACCESS_COOKIE,
  ACCESS_MAX_AGE,
  BACKEND_URL,
  cookieOptions,
  decodeJwt,
  REFRESH_COOKIE,
  REFRESH_MAX_AGE,
} from "@/lib/auth-config";

export async function POST(request: Request) {
  const { email, password } = await request.json();
  const res = await fetch(`${BACKEND_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const message =
      res.status === 401
        ? "Correo o contraseña incorrectos."
        : "No se pudo iniciar sesión. Intenta de nuevo.";
    return NextResponse.json({ error: message }, { status: res.status });
  }

  const tokens = await res.json();
  const role = decodeJwt(tokens.access_token)?.role ?? null;

  const jar = await cookies();
  jar.set(ACCESS_COOKIE, tokens.access_token, cookieOptions(ACCESS_MAX_AGE));
  jar.set(REFRESH_COOKIE, tokens.refresh_token, cookieOptions(REFRESH_MAX_AGE));

  return NextResponse.json({ role });
}

export async function DELETE() {
  const jar = await cookies();
  jar.delete(ACCESS_COOKIE);
  jar.delete(REFRESH_COOKIE);
  return NextResponse.json({ ok: true });
}
