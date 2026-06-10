"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { ApiError, apiDelete, apiGet, apiPatch } from "@/lib/api";
import { formatCantidad, formatCOP } from "@/lib/money";
import type { MovementRead, Product, Supplier } from "@/lib/types";

import AdminGuard from "../../AdminGuard";
import MovimientoForm from "../MovimientoForm";
import ProductoForm from "../ProductoForm";

const TIPO_LABEL: Record<string, string> = {
  entrada: "Entrada",
  salida: "Salida",
  merma: "Merma",
  ajuste: "Ajuste",
  reverso_venta: "Reverso",
};

export default function ProductoDetallePage() {
  const router = useRouter();
  const params = useParams();
  const id = Number(params.id);
  const [product, setProduct] = useState<Product | null>(null);
  const [proveedores, setProveedores] = useState<Supplier[]>([]);
  const [kardex, setKardex] = useState<MovementRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    const [p, provs, mov] = await Promise.all([
      apiGet<Product>(`products/${id}`),
      apiGet<Supplier[]>("suppliers").catch(() => []),
      apiGet<MovementRead[]>(`products/${id}/kardex`).catch(() => []),
    ]);
    setProduct(p);
    setProveedores(provs);
    setKardex(mov);
  }, [id]);

  useEffect(() => {
    let cancel = false;
    (async () => {
      try {
        await cargar();
      } catch {
        if (!cancel) setError("No se pudo cargar el producto.");
      } finally {
        if (!cancel) setLoading(false);
      }
    })();
    return () => {
      cancel = true;
    };
  }, [cargar]);

  async function toggleActivo() {
    if (!product) return;
    setError(null);
    try {
      if (product.activo) {
        await apiDelete(`products/${product.id}`); // soft-delete
      } else {
        await apiPatch(`products/${product.id}`, { activo: true }); // reactivar
      }
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cambiar el estado.");
    }
  }

  if (loading) return <p className="text-grafito">Cargando…</p>;
  if (!product) return <p className="text-grafito">{error ?? "Producto no encontrado."}</p>;

  return (
    <AdminGuard>
      <Link href="/inventario" className="text-sm text-azulon hover:underline">
        ← Inventario
      </Link>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
        <h1 className="font-display text-2xl font-bold text-tinta">
          {product.nombre}
          {!product.activo && <span className="ml-2 text-sm font-normal text-grafito">(inactivo)</span>}
        </h1>
        <button
          onClick={toggleActivo}
          className="rounded-md border border-niebla px-3 py-1.5 text-sm font-medium text-tinta transition hover:bg-niebla/60"
        >
          {product.activo ? "Desactivar" : "Reactivar"}
        </button>
      </div>

      {error && (
        <div role="alert" className="mt-3 rounded-lg border border-achiote/30 bg-achiote/10 px-3 py-2 text-sm text-achiote">
          {error}
        </div>
      )}

      <div className="mt-4 grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <section>
          <h2 className="mb-2 text-sm font-bold uppercase tracking-wide text-grafito">Atributos</h2>
          <ProductoForm producto={product} proveedores={proveedores} onDone={() => router.push("/inventario")} />
        </section>

        <div className="space-y-6">
          <section className="rounded-2xl border border-niebla bg-white p-4">
            <h2 className="mb-2 text-sm font-bold uppercase tracking-wide text-grafito">
              Merma / Ajuste
            </h2>
            <MovimientoForm product={product} onDone={cargar} />
          </section>

          <section className="rounded-2xl border border-niebla bg-white p-4">
            <h2 className="mb-2 text-sm font-bold uppercase tracking-wide text-grafito">
              Kardex (movimientos)
            </h2>
            {kardex.length === 0 ? (
              <p className="text-sm text-grafito">Sin movimientos todavía.</p>
            ) : (
              <table className="w-full text-sm">
                <thead className="text-left text-grafito">
                  <tr>
                    <th className="py-1 font-medium">Tipo</th>
                    <th className="py-1 text-right font-medium">Cant.</th>
                    <th className="py-1 text-right font-medium">Saldo</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-niebla">
                  {kardex.map((m) => (
                    <tr key={m.id}>
                      <td className="py-1.5 text-tinta">
                        {TIPO_LABEL[m.tipo] ?? m.tipo}
                        {m.costo_unitario_centavos != null && (
                          <span className="tabular block text-xs text-grafito">
                            {formatCOP(m.costo_unitario_centavos)} c/u
                          </span>
                        )}
                      </td>
                      <td className="tabular py-1.5 text-right text-tinta">
                        {formatCantidad(m.cantidad_milesimas)}
                      </td>
                      <td className="tabular py-1.5 text-right text-grafito">
                        {formatCantidad(m.stock_resultante_milesimas)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </div>
      </div>
    </AdminGuard>
  );
}
