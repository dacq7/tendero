"use client";

import { useEffect, useState } from "react";

import { ApiError, apiGet, apiPost } from "@/lib/api";
import { formatCOP } from "@/lib/money";
import type { CashSession } from "@/lib/types";

function pesosToCentavos(pesos: string): number {
  return Math.round(Number(pesos || 0) * 100);
}

export default function CajaPage() {
  const [cash, setCash] = useState<CashSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [montoInicial, setMontoInicial] = useState("");
  const [contado, setContado] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      const current = await apiGet<CashSession>("cash/sessions/current");
      setCash(current);
    } catch {
      setCash(null); // 409: no hay caja abierta
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let cancel = false;
    (async () => {
      try {
        const current = await apiGet<CashSession>("cash/sessions/current");
        if (!cancel) setCash(current);
      } catch {
        if (!cancel) setCash(null); // 409: no hay caja abierta
      } finally {
        if (!cancel) setLoading(false);
      }
    })();
    return () => {
      cancel = true;
    };
  }, []);

  async function abrir() {
    setError(null);
    setBusy(true);
    try {
      await apiPost<CashSession>("cash/sessions", {
        monto_inicial_centavos: pesosToCentavos(montoInicial),
      });
      setMontoInicial("");
      await refresh();
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
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cerrar la caja.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <p className="text-grafito">Cargando caja…</p>;

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
        <div className="mt-6 rounded-2xl border border-niebla bg-white p-5">
          <p className="text-sm font-medium text-azulon">Caja abierta</p>
          <dl className="mt-3 space-y-1 text-sm">
            <div className="flex justify-between text-grafito">
              <dt>Monto inicial</dt>
              <dd className="tabular">{formatCOP(cash.monto_inicial_centavos)}</dd>
            </div>
          </dl>
          <label htmlFor="contado" className="mt-5 block text-sm font-medium text-tinta">
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
    </div>
  );
}

function Linea({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="flex justify-between text-grafito">
      <dt>{label}</dt>
      <dd className="tabular">{formatCOP(value ?? 0)}</dd>
    </div>
  );
}
