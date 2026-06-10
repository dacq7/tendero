"use client";

// Piezas compartidas del dashboard de analítica: hook de fetch lazy, tarjetas,
// paneles, formateadores y descarga CSV por sección. Dirección "Rótulo": denso
// pero claro, cifras en mono tabular, sin tarjetas vacías ni gradientes.

import { useEffect, useState } from "react";

import { ApiError, apiGet } from "@/lib/api";

export const MARCA = "#173f8a"; // azulón
export const ACCION = "#e8552b"; // achiote
export const GRAFITO = "#5c5f66";
export const NIEBLA = "#e4e1da";
export const VERDE = "#1f7a4d";

export interface Rango {
  desde: string;
  hasta: string;
}

/** Estado de una carga: data | cargando | error (incluye 403 → solo admin). */
export interface Fetch<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  denegado: boolean;
}

const CARGANDO: Fetch<never> = { data: null, loading: true, error: null, denegado: false };

/** Carga lazy: corre `fn` cuando cambian las deps; cancela si se desmonta.
 * El estado solo se actualiza DESPUÉS del await (nunca síncrono en el efecto),
 * para no disparar renders en cascada. Mientras se recarga deja ver lo anterior. */
export function useFetch<T>(fn: () => Promise<T>, deps: unknown[]): Fetch<T> {
  const [state, setState] = useState<Fetch<T>>(CARGANDO);
  useEffect(() => {
    let cancel = false;
    (async () => {
      try {
        const data = await fn();
        if (!cancel) setState({ data, loading: false, error: null, denegado: false });
      } catch (err) {
        if (cancel) return;
        const denegado = err instanceof ApiError && err.status === 403;
        setState({
          data: null,
          loading: false,
          denegado,
          error: denegado ? null : "No se pudieron cargar los datos.",
        });
      }
    })();
    return () => {
      cancel = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return state;
}

/** GET tipado con query de rango ya armada. */
export function getRango<T>(path: string, r: Rango, extra = ""): Promise<T> {
  return apiGet<T>(`${path}?desde=${r.desde}&hasta=${r.hasta}${extra}`);
}

/** Dispara la descarga del CSV server-side de un dataset para el rango actual. */
export function exportarCsv(dataset: string, r: Rango, gran?: string): void {
  const g = gran ? `&granularidad=${gran}` : "";
  window.location.href = `/api/proxy/analytics/export.csv?dataset=${dataset}&desde=${r.desde}&hasta=${r.hasta}${g}`;
}

// ── Formateadores de cifras ──

/** Rotación en veces/año desde centi (350 → "3,50×"). */
export function formatVeces(centi: number | null): string {
  if (centi === null) return "—";
  return `${(centi / 100).toLocaleString("es-CO", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}×`;
}

/** bps → porcentaje (4047 → "40,5%"). */
export function formatPct(bps: number | null): string {
  if (bps === null) return "—";
  return `${(bps / 100).toLocaleString("es-CO", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;
}

export function deltaTexto(bps: number | null): { texto: string; positivo: boolean } | null {
  if (bps === null) return null;
  return { texto: `${bps >= 0 ? "+" : ""}${(bps / 100).toFixed(1)}%`, positivo: bps >= 0 };
}

// ── Componentes ──

export function Kpi({
  label,
  valor,
  sub,
  delta,
}: {
  label: string;
  valor: string;
  sub?: string;
  delta?: { texto: string; positivo: boolean } | null;
}) {
  return (
    <div className="rounded-xl border border-niebla bg-white p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-grafito">{label}</p>
      <p className="tabular mt-1 text-2xl font-bold text-tinta">{valor}</p>
      {(sub || delta) && (
        <div className="mt-1 flex items-center gap-2 text-xs">
          {sub && <span className="tabular text-grafito">{sub}</span>}
          {delta && (
            <span className={delta.positivo ? "text-[#1f7a4d]" : "text-achiote"}>
              {delta.texto}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

export function Panel({
  titulo,
  children,
  acciones,
}: {
  titulo: string;
  children: React.ReactNode;
  acciones?: React.ReactNode;
}) {
  return (
    <section className="mt-4 rounded-2xl border border-niebla bg-white p-4">
      <div className="mb-2 flex items-center justify-between gap-2">
        <h2 className="font-display text-sm font-bold uppercase tracking-wide text-grafito">
          {titulo}
        </h2>
        {acciones}
      </div>
      {children}
    </section>
  );
}

export function BotonCsv({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="rounded-md border border-niebla px-2.5 py-1 text-xs font-medium text-tinta transition hover:bg-niebla/60"
    >
      Exportar CSV
    </button>
  );
}

/** Estado de carga / vacío / error, en la voz de la interfaz. */
export function Estado({
  fetch,
  vacio,
  children,
}: {
  fetch: Fetch<unknown>;
  vacio?: boolean;
  children: React.ReactNode;
}) {
  if (fetch.denegado) {
    return <p className="mt-6 text-grafito">Esta sección es solo para administradores.</p>;
  }
  if (fetch.loading) return <p className="mt-6 text-grafito">Cargando…</p>;
  if (fetch.error) return <p className="mt-6 text-achiote">{fetch.error}</p>;
  if (vacio) {
    return (
      <p className="mt-6 text-grafito">Sin datos en este periodo. Prueba un rango más amplio.</p>
    );
  }
  return <>{children}</>;
}
