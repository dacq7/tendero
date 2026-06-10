// Protege las rutas privadas: sin sesión (cookie de refresh) → /login.
// Si ya hay sesión y se visita /login → al mostrador. La autoridad real de
// permisos es el backend; esto solo evita mostrar páginas sin sesión.
// (Convención `proxy` de Next 16, reemplaza al antiguo `middleware`.)

import { NextRequest, NextResponse } from "next/server";

import { REFRESH_COOKIE } from "@/lib/auth-config";

const PROTECTED = ["/vender", "/caja", "/inventario", "/historial"];

export default function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasSession = Boolean(request.cookies.get(REFRESH_COOKIE)?.value);

  const isProtected = PROTECTED.some(
    (p) => pathname === p || pathname.startsWith(`${p}/`),
  );

  if (isProtected && !hasSession) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }

  if (pathname === "/login" && hasSession) {
    const url = request.nextUrl.clone();
    url.pathname = "/vender";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/vender/:path*", "/caja/:path*", "/inventario/:path*", "/historial/:path*", "/login"],
};
