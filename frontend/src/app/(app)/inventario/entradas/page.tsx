"use client";

import Link from "next/link";
import { type FormEvent, useEffect, useState } from "react";

import { ApiError, apiGet, apiPost } from "@/lib/api";
import { pesosACentavos, unidadesAMilesimas } from "@/lib/forms";
import type { Product, Supplier } from "@/lib/types";

import AdminGuard from "../../AdminGuard";

interface Linea {
  product_id: string;
  cantidad: string; // unidades
  costo: string; // pesos
}

const lineaVacia = (): Linea => ({ product_id: "", cantidad: "", costo: "" });

export default function EntradasPage() {
  const [productos, setProductos] = useState<Product[]>([]);
  const [proveedores, setProveedores] = useState<Supplier[]>([]);
  const [supplierId, setSupplierId] = useState("");
  const [motivo, setMotivo] = useState("");
  const [lineas, setLineas] = useState<Linea[]>([lineaVacia()]);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancel = false;
    Promise.all([
      apiGet<Product[]>("products?limit=200").catch(() => []),
      apiGet<Supplier[]>("suppliers").catch(() => []),
    ]).then(([p, s]) => {
      if (cancel) return;
      setProductos(p);
      setProveedores(s);
    });
    return () => {
      cancel = true;
    };
  }, []);

  function setLinea(i: number, patch: Partial<Linea>) {
    setLineas((ls) => ls.map((l, idx) => (idx === i ? { ...l, ...patch } : l)));
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setOk(false);
    const payloadLineas = lineas
      .filter((l) => l.product_id && unidadesAMilesimas(l.cantidad) > 0)
      .map((l) => ({
        product_id: Number(l.product_id),
        cantidad_milesimas: unidadesAMilesimas(l.cantidad),
        costo_unitario_centavos: pesosACentavos(l.costo),
      }));
    if (payloadLineas.length === 0) {
      setError("Agrega al menos una línea con producto y cantidad.");
      return;
    }
    setBusy(true);
    try {
      await apiPost("inventory/entries", {
        supplier_id: supplierId ? Number(supplierId) : null,
        motivo: motivo || null,
        lineas: payloadLineas,
      });
      setOk(true);
      setLineas([lineaVacia()]);
      setMotivo("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo registrar la entrada.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AdminGuard>
      <div className="max-w-2xl">
      <Link href="/inventario" className="text-sm text-azulon hover:underline">
        ← Inventario
      </Link>
      <h1 className="mt-2 font-display text-2xl font-bold text-tinta">Entrada de mercancía</h1>
      <p className="mt-1 text-sm text-grafito">
        Registra la llegada de mercancía. Suma stock y recalcula el costo promedio (CMP).
      </p>

      <form onSubmit={submit} className="mt-4 space-y-4">
        {error && (
          <div role="alert" className="rounded-lg border border-achiote/30 bg-achiote/10 px-3 py-2 text-sm text-achiote">
            {error}
          </div>
        )}
        {ok && (
          <div className="rounded-lg border border-azulon/30 bg-azulon/5 px-3 py-2 text-sm text-azulon">
            Entrada registrada. El stock y el costo se actualizaron.
          </div>
        )}

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block text-sm font-medium text-tinta">
            Proveedor
            <select value={supplierId} onChange={(e) => setSupplierId(e.target.value)} className={inputCls}>
              <option value="">— Sin proveedor —</option>
              {proveedores.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.nombre}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm font-medium text-tinta">
            Motivo
            <input value={motivo} onChange={(e) => setMotivo(e.target.value)} className={inputCls} placeholder="Compra, reposición…" />
          </label>
        </div>

        <div className="space-y-2">
          {lineas.map((l, i) => (
            <div key={i} className="grid grid-cols-[1fr_auto_auto_auto] items-end gap-2">
              <label className="block text-xs font-medium text-grafito">
                Producto
                <select
                  value={l.product_id}
                  onChange={(e) => setLinea(i, { product_id: e.target.value })}
                  aria-label={`Producto línea ${i + 1}`}
                  className={inputCls}
                >
                  <option value="">— Elegir —</option>
                  {productos.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.nombre}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-xs font-medium text-grafito">
                Cantidad
                <input
                  type="number"
                  min={0}
                  step={1}
                  value={l.cantidad}
                  onChange={(e) => setLinea(i, { cantidad: e.target.value })}
                  aria-label={`Cantidad línea ${i + 1}`}
                  className={`${inputCls} tabular w-24 text-right`}
                />
              </label>
              <label className="block text-xs font-medium text-grafito">
                Costo (pesos)
                <input
                  type="number"
                  min={0}
                  step={1}
                  value={l.costo}
                  onChange={(e) => setLinea(i, { costo: e.target.value })}
                  aria-label={`Costo línea ${i + 1}`}
                  className={`${inputCls} tabular w-28 text-right`}
                />
              </label>
              <button
                type="button"
                onClick={() => setLineas((ls) => (ls.length > 1 ? ls.filter((_, idx) => idx !== i) : ls))}
                aria-label={`Quitar línea ${i + 1}`}
                className="h-11 w-11 rounded-lg border border-niebla text-grafito transition hover:text-achiote"
              >
                ✕
              </button>
            </div>
          ))}
          <button
            type="button"
            onClick={() => setLineas((ls) => [...ls, lineaVacia()])}
            className="rounded-md border border-niebla px-3 py-1.5 text-sm font-medium text-tinta transition hover:bg-niebla/60"
          >
            + Agregar línea
          </button>
        </div>

        <button
          type="submit"
          disabled={busy}
          className="h-12 w-full rounded-xl bg-achiote font-semibold text-papel transition hover:brightness-105 disabled:opacity-60"
        >
          {busy ? "Registrando…" : "Registrar entrada"}
        </button>
      </form>
      </div>
    </AdminGuard>
  );
}

const inputCls =
  "mt-1 h-11 w-full rounded-lg border border-niebla bg-white px-3 text-tinta outline-none transition focus:border-azulon focus:ring-2 focus:ring-azulon/30";
