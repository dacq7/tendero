// Proxy server-side: adjunta el access token (cookie httpOnly) a las llamadas al
// backend. Si el backend responde 401, intenta refrescar una vez y reintenta,
// rotando las cookies. El access token JAMÁS llega al navegador.

import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import {
  ACCESS_COOKIE,
  ACCESS_MAX_AGE,
  BACKEND_URL,
  cookieOptions,
  REFRESH_COOKIE,
  REFRESH_MAX_AGE,
} from "@/lib/auth-config";

type Ctx = { params: Promise<{ path: string[] }> };

// Allowlist de prefijos: el proxy solo reenvía a endpoints conocidos del
// backend (evita SSRF/enumeración de rutas internas o de fases futuras).
const ALLOWED_PREFIXES = [
  "products",
  "suppliers",
  "inventory",
  "sales",
  "cash",
  "invoices",
  "auth/me",
];

function isAllowed(path: string[]): boolean {
  const joined = path.join("/");
  return ALLOWED_PREFIXES.some((p) => joined === p || joined.startsWith(`${p}/`));
}

async function forward(request: Request, ctx: Ctx): Promise<NextResponse> {
  const { path } = await ctx.params;
  if (!isAllowed(path)) {
    return NextResponse.json({ detail: "Ruta no permitida" }, { status: 403 });
  }

  const jar = await cookies();
  const access = jar.get(ACCESS_COOKIE)?.value;
  const refresh = jar.get(REFRESH_COOKIE)?.value;

  const search = new URL(request.url).search;
  const target = `${BACKEND_URL}/${path.join("/")}${search}`;
  const method = request.method;
  const rawBody =
    method === "GET" || method === "HEAD" ? undefined : await request.text();

  const call = (token: string | undefined) =>
    fetch(target, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: rawBody || undefined,
    });

  let res = await call(access);
  let rotated: { access: string; refresh: string } | null = null;
  let refreshFailed = false;

  if (res.status === 401 && refresh) {
    const rr = await fetch(`${BACKEND_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (rr.ok) {
      const t = await rr.json();
      rotated = { access: t.access_token, refresh: t.refresh_token };
      res = await call(t.access_token);
    } else {
      refreshFailed = true; // refresh inválido/expirado → desloguear limpio
    }
  }

  const out =
    res.status === 204
      ? new NextResponse(null, { status: 204 })
      : new NextResponse(await res.text(), {
          status: res.status,
          headers: {
            "Content-Type": res.headers.get("Content-Type") ?? "application/json",
          },
        });

  if (rotated) {
    out.cookies.set(ACCESS_COOKIE, rotated.access, cookieOptions(ACCESS_MAX_AGE));
    out.cookies.set(REFRESH_COOKIE, rotated.refresh, cookieOptions(REFRESH_MAX_AGE));
  }
  if (refreshFailed) {
    // Cookies huérfanas: bórralas para que el cliente quede deslogueado.
    out.cookies.delete(ACCESS_COOKIE);
    out.cookies.delete(REFRESH_COOKIE);
  }
  return out;
}

export const GET = forward;
export const POST = forward;
export const PATCH = forward;
export const PUT = forward;
export const DELETE = forward;
