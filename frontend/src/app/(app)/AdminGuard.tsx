"use client";

// Gate de presentación para pantallas de gestión (solo admin). NO es la autoridad
// real (el backend ya valida con require_role); evita mostrar formularios de
// escritura a un cajero y le da un mensaje claro en vez de un error de la API.

import { useEffect, useState } from "react";

import { apiGet } from "@/lib/api";
import type { UserMe } from "@/lib/types";

export default function AdminGuard({ children }: { children: React.ReactNode }) {
  const [estado, setEstado] = useState<"cargando" | "admin" | "denegado">("cargando");

  useEffect(() => {
    let cancel = false;
    apiGet<UserMe>("auth/me")
      .then((u) => !cancel && setEstado(u.role === "admin" ? "admin" : "denegado"))
      .catch(() => !cancel && setEstado("denegado"));
    return () => {
      cancel = true;
    };
  }, []);

  if (estado === "cargando") return <p className="text-grafito">Cargando…</p>;
  if (estado === "denegado") {
    return <p className="text-grafito">Esta sección es solo para administradores.</p>;
  }
  return <>{children}</>;
}
