"use client";

import { type FormEvent, useState } from "react";

import { ApiError, apiPost } from "@/lib/api";
import { unidadesAMilesimas } from "@/lib/forms";
import type { Product } from "@/lib/types";

// Solo merma y ajuste se registran aquí. La ENTRADA va por la pantalla de entrada
// de mercancía (con costo, recalcula CMP). La SALIDA por venta es automática.
type Tipo = "merma" | "ajuste";

export default function MovimientoForm({
  product,
  onDone,
}: {
  product: Product;
  onDone: () => void;
}) {
  const [tipo, setTipo] = useState<Tipo>("merma");
  const [cantidad, setCantidad] = useState("");
  const [motivo, setMotivo] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const cant = unidadesAMilesimas(cantidad);
    if (cant <= 0) {
      setError("La cantidad debe ser mayor que cero.");
      return;
    }
    setBusy(true);
    try {
      // merma: magnitud a descontar. ajuste: stock OBJETIVO (la API fija el stock a ese valor).
      await apiPost("inventory/movements", {
        product_id: product.id,
        tipo,
        cantidad_milesimas: cant,
        motivo: motivo || null,
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo registrar el movimiento.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      {error && (
        <div role="alert" className="rounded-lg border border-achiote/30 bg-achiote/10 px-3 py-2 text-sm text-achiote">
          {error}
        </div>
      )}
      <div className="flex gap-2">
        {(["merma", "ajuste"] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTipo(t)}
            aria-pressed={tipo === t}
            className={`h-10 flex-1 rounded-lg border text-sm font-medium capitalize transition ${
              tipo === t ? "border-azulon bg-azulon/10 text-azulon" : "border-niebla text-grafito"
            }`}
          >
            {t}
          </button>
        ))}
      </div>
      <label className="block text-sm font-medium text-tinta">
        {tipo === "ajuste" ? "Nuevo stock objetivo (unidades)" : "Cantidad a descontar (unidades)"}
        <input
          type="number"
          min={0}
          step={1}
          value={cantidad}
          onChange={(e) => setCantidad(e.target.value)}
          aria-label="Cantidad del movimiento"
          className="tabular mt-1 h-11 w-full rounded-lg border border-niebla px-3 text-right outline-none focus:border-azulon focus:ring-2 focus:ring-azulon/30"
        />
      </label>
      <label className="block text-sm font-medium text-tinta">
        Motivo
        <input
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
          placeholder={tipo === "merma" ? "Vencido, dañado…" : "Corrección de conteo"}
          className="mt-1 h-11 w-full rounded-lg border border-niebla px-3 outline-none focus:border-azulon focus:ring-2 focus:ring-azulon/30"
        />
      </label>
      <button
        type="submit"
        disabled={busy}
        className="h-11 w-full rounded-lg bg-tinta font-semibold text-papel transition hover:brightness-110 disabled:opacity-60"
      >
        {busy ? "Registrando…" : "Registrar movimiento"}
      </button>
    </form>
  );
}
