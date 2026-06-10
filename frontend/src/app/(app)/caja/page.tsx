"use client";

import { useEffect, useState } from "react";

import { ApiError, apiGet, apiPost } from "@/lib/api";
import { formatCOP } from "@/lib/money";
import type { CashSession, CashSessionDetail, SaleRead } from "@/lib/types";

function pesosToCentavos(pesos: string): number {
  // El cajero cuenta efectivo en pesos ENTEROS (COP no circula con centavos).
  // Redondeamos a peso entero ANTES de *100 → resultado entero exacto (sin float).
  const enteros = Math.round(Number(pesos || 0));
  return Number.isFinite(enteros) ? enteros * 100 : 0;
}

const METODO_LABEL: Record<string, string> = {
  efectivo: "Efectivo",
  transferencia: "Transferencia",
  tarjeta: "Tarjeta",
  pse: "PSE",
  nequi: "Nequi",
};

export default function CajaPage() {
  const [cash, setCash] = useState<CashSession | null>(null);
  const [detail, setDetail] = useState<CashSessionDetail | null>(null);
  const [historial, setHistorial] = useState<CashSession[]>([]);
  const [nTx, setNTx] = useState(0);
  const [loading, setLoading] = useState(true);
  const [montoInicial, setMontoInicial] = useState("");
  const [contado, setContado] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Carga la caja abierta y su resumen del turno (totales por método + nº ventas).
  async function cargar() {
    try {
      const current = await apiGet<CashSession>("cash/sessions/current");
      setCash(current);
      if (current.status === "abierta") {
        const [det, ventas] = await Promise.all([
          apiGet<CashSessionDetail>(`cash/sessions/${current.id}`),
          apiGet<SaleRead[]>(`sales?cash_session_id=${current.id}`),
        ]);
        setDetail(det);
        setNTx(ventas.length);
      }
    } catch {
      setCash(null); // 409: no hay caja abierta
      setDetail(null);
    }
    // Historial de cajas cerradas (consultable). El backend filtra por dueño/admin.
    const todas = (await apiGet<CashSession[]>("cash/sessions").catch(() => [])) ?? [];
    setHistorial(todas.filter((c) => c.status === "cerrada"));
  }

  useEffect(() => {
    let cancel = false;
    (async () => {
      await cargar();
      if (!cancel) setLoading(false);
    })();
    return () => {
      cancel = true;
    };
  }, []);

  async function refrescar() {
    setBusy(true);
    await cargar();
    setBusy(false);
  }

  async function abrir() {
    setError(null);
    setBusy(true);
    try {
      await apiPost<CashSession>("cash/sessions", {
        monto_inicial_centavos: pesosToCentavos(montoInicial),
      });
      setMontoInicial("");
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo abrir la caja.");
    } finally {
      setBusy(false);
    }
  }

  async function cerrar() {
    if (!cash) return;
    setError(null);
    setBusy(true);
    try {
      const cerrada = await apiPost<CashSession>(`cash/sessions/${cash.id}/close`, {
        efectivo_contado_centavos: pesosToCentavos(contado),
      });
      setCash(cerrada);
      setDetail(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cerrar la caja.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <p className="text-grafito">Cargando caja…</p>;

  const totalTurno = detail
    ? Object.values(detail.totales_por_metodo).reduce((a, b) => a + b, 0)
    : 0;
  const efectivoTurno = detail?.totales_por_metodo["efectivo"] ?? 0;
  const esperadoEfectivo = (cash?.monto_inicial_centavos ?? 0) + efectivoTurno;

  return (
    <div className="mx-auto max-w-md">
      <h1 className="font-display text-2xl font-bold text-tinta">Caja</h1>

      {error && (
        <div role="alert" className="mt-4 rounded-lg border border-achiote/30 bg-achiote/10 px-3 py-2 text-sm text-achiote">
          {error}
        </div>
      )}

      {!cash && (
        <div className="mt-6 rounded-2xl border border-niebla bg-white p-5">
          <p className="text-sm text-grafito">No hay caja abierta. Ábrela para empezar a vender.</p>
          <label htmlFor="monto" className="mt-4 block text-sm font-medium text-tinta">
            Monto inicial (base)
          </label>
          <input
            id="monto"
            type="number"
            min={0}
            step={1}
            value={montoInicial}
            onChange={(e) => setMontoInicial(e.target.value)}
            placeholder="0"
            className="tabular mt-1.5 h-12 w-full rounded-lg border border-niebla px-3 text-right"
          />
          <button
            onClick={abrir}
            disabled={busy}
            className="mt-4 h-12 w-full rounded-xl bg-achiote font-semibold text-papel transition hover:brightness-105 disabled:opacity-60"
          >
            {busy ? "Abriendo…" : "Abrir caja"}
          </button>
        </div>
      )}

      {cash && cash.status === "abierta" && (
        <div className="mt-6 space-y-4">
          {/* Resumen del turno en vivo (refrescable). */}
          <div className="rounded-2xl border border-niebla bg-white p-5">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-azulon">Caja abierta · turno actual</p>
              <button
                onClick={refrescar}
                disabled={busy}
                className="rounded-md border border-niebla px-2.5 py-1 text-xs font-medium text-tinta transition hover:bg-niebla/60 disabled:opacity-60"
              >
                {busy ? "…" : "Refrescar"}
              </button>
            </div>
            <dl className="mt-3 space-y-1 text-sm">
              <Linea label="Monto inicial" value={cash.monto_inicial_centavos} />
              <Linea label="Vendido en el turno" value={totalTurno} fuerte />
              <div className="flex justify-between text-grafito">
                <dt>Transacciones</dt>
                <dd className="tabular" data-testid="n-tx">
                  {nTx}
                </dd>
              </div>
            </dl>

            {detail && Object.keys(detail.totales_por_metodo).length > 0 && (
              <dl className="mt-3 space-y-1 border-t border-niebla pt-3 text-sm">
                {Object.entries(detail.totales_por_metodo).map(([metodo, total]) => (
                  <div key={metodo} className="flex justify-between text-grafito">
                    <dt className="capitalize">{METODO_LABEL[metodo] ?? metodo}</dt>
                    <dd className="tabular">{formatCOP(total)}</dd>
                  </div>
                ))}
              </dl>
            )}

            <dl className="mt-3 border-t border-niebla pt-3 text-sm">
              <div className="flex justify-between font-medium text-tinta">
                <dt>Esperado en efectivo</dt>
                <dd className="tabular" data-testid="esperado-efectivo">
                  {formatCOP(esperadoEfectivo)}
                </dd>
              </div>
              <p className="mt-1 text-xs text-grafito">
                Monto inicial + ventas en efectivo del turno.
              </p>
            </dl>
          </div>

          {/* Arqueo / cierre. */}
          <div className="rounded-2xl border border-niebla bg-white p-5">
            <label htmlFor="contado" className="block text-sm font-medium text-tinta">
              Efectivo contado (arqueo)
            </label>
            <input
              id="contado"
              type="number"
              min={0}
              step={1}
              value={contado}
              onChange={(e) => setContado(e.target.value)}
              placeholder="0"
              className="tabular mt-1.5 h-12 w-full rounded-lg border border-niebla px-3 text-right"
            />
            <button
              onClick={cerrar}
              disabled={busy}
              className="mt-4 h-12 w-full rounded-xl bg-tinta font-semibold text-papel transition hover:brightness-110 disabled:opacity-60"
            >
              {busy ? "Cerrando…" : "Cerrar caja con arqueo"}
            </button>
          </div>
        </div>
      )}

      {cash && cash.status === "cerrada" && (
        <div className="mt-6 rounded-2xl border border-niebla bg-white p-5">
          <p className="text-sm font-medium text-tinta">Caja cerrada — arqueo</p>
          <dl className="mt-3 space-y-1 text-sm">
            <Linea label="Esperado" value={cash.efectivo_esperado_centavos} />
            <Linea label="Contado" value={cash.efectivo_contado_centavos} />
            <div
              className={`flex justify-between pt-1 font-bold ${
                (cash.diferencia_centavos ?? 0) < 0 ? "text-achiote" : "text-tinta"
              }`}
            >
              <dt>Diferencia</dt>
              <dd className="tabular">{formatCOP(cash.diferencia_centavos ?? 0)}</dd>
            </div>
          </dl>
        </div>
      )}

      {historial.length > 0 && (
        <section className="mt-8">
          <h2 className="text-sm font-bold uppercase tracking-wide text-grafito">
            Cajas anteriores
          </h2>
          <div className="mt-2 overflow-hidden rounded-2xl border border-niebla bg-white">
            <table className="w-full text-sm">
              <thead className="border-b border-niebla bg-niebla/30 text-left text-grafito">
                <tr>
                  <th className="px-4 py-2 font-medium">Cierre</th>
                  <th className="px-4 py-2 text-right font-medium">Esperado</th>
                  <th className="px-4 py-2 text-right font-medium">Contado</th>
                  <th className="px-4 py-2 text-right font-medium">Diferencia</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-niebla">
                {historial.map((c) => (
                  <tr key={c.id}>
                    <td className="px-4 py-2 text-grafito">
                      {c.cerrada_at ? new Date(c.cerrada_at).toLocaleString("es-CO") : "—"}
                    </td>
                    <td className="tabular px-4 py-2 text-right text-tinta">
                      {formatCOP(c.efectivo_esperado_centavos ?? 0)}
                    </td>
                    <td className="tabular px-4 py-2 text-right text-tinta">
                      {formatCOP(c.efectivo_contado_centavos ?? 0)}
                    </td>
                    <td
                      className={`tabular px-4 py-2 text-right ${
                        (c.diferencia_centavos ?? 0) < 0 ? "text-achiote" : "text-tinta"
                      }`}
                    >
                      {formatCOP(c.diferencia_centavos ?? 0)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

function Linea({
  label,
  value,
  fuerte,
}: {
  label: string;
  value: number | null;
  fuerte?: boolean;
}) {
  return (
    <div className={`flex justify-between ${fuerte ? "font-bold text-tinta" : "text-grafito"}`}>
      <dt>{label}</dt>
      <dd className="tabular">{formatCOP(value ?? 0)}</dd>
    </div>
  );
}
