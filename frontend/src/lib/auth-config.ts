// Configuración de sesión compartida por route handlers (Node) y middleware
// (Edge). Sin imports de Node: edge-safe. Los JWT viven SOLO en cookies httpOnly;
// el navegador nunca los ve.

// Solo server-side (route handlers/proxy). No usar NEXT_PUBLIC_* aquí: se
// embebería en el bundle del cliente y sería un vector de SSRF configurable.
export const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8020";

export const ACCESS_COOKIE = "tendero_access";
export const REFRESH_COOKIE = "tendero_refresh";

export const ACCESS_MAX_AGE = 15 * 60; // 15 min (coincide con el access del backend)
export const REFRESH_MAX_AGE = 7 * 24 * 60 * 60; // 7 días

export function cookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production", // en local (http) no exige https
    sameSite: "lax" as const,
    path: "/",
    maxAge,
  };
}

export interface JwtPayload {
  sub: string;
  role: string;
  type: string;
  exp: number;
}

/** ⚠️ SOLO para UI (orientar la navegación). NO usar para decisiones de
 * autorización server-side: NO verifica la firma del JWT. La autoridad real
 * de permisos es siempre el backend. */
export function decodeJwt(token: string): JwtPayload | null {
  const part = token.split(".")[1];
  if (!part) return null;
  const b64 = part.replace(/-/g, "+").replace(/_/g, "/");
  try {
    const json =
      typeof atob !== "undefined"
        ? atob(b64)
        : Buffer.from(b64, "base64").toString("utf-8");
    return JSON.parse(json) as JwtPayload;
  } catch {
    return null;
  }
}
