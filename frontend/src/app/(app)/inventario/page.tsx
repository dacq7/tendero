"use client";

import { useEffect, useState } from "react";

import { apiGet } from "@/lib/api";
import { formatCantidad, formatCOP } from "@/lib/money";
import type { Product } from "@/lib/types";

export default function InventarioPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [alertas, setAlertas] = useState<Product[]>([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancel = false;
    (async () => {
      const [list, low] = await Promise.all([
        apiGet<Product[]>(`products?q=${encodeURIComponent(q)}&limit=100`).catch(() => []),
        apiGet<Product[]>("inventory/alerts/low-stock").catch(() => []),
      ]);
      if (cancel) return;
      setProducts(list);
      setAlertas(low);
      setLoading(false);
    })();
    return () => {
      cancel = true;
    };
  }, [q]);

  return (
    <div>
      <div className="flex items-center justify-between gap-4">
        <h1 className="font-display text-2xl font-bold text-tinta">Inventario</h1>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Buscar…"
          className="h-10 w-56 rounded-lg border border-niebla px-3 text-sm"
        />
      </div>

      {alertas.length > 0 && (
        <div className="mt-4 rounded-xl border border-achiote/30 bg-achiote/5 p-3">
          <p className="text-sm font-medium text-achiote">
            {alertas.length} producto(s) con stock bajo
          </p>
          <p className="tabular mt-1 text-xs text-grafito">
            {alertas.map((a) => a.nombre).join(" · ")}
          </p>
        </div>
      )}

      <div className="mt-4 overflow-hidden rounded-2xl border border-niebla bg-white">
        <table className="w-full text-sm">
          <thead className="border-b border-niebla bg-niebla/30 text-left text-grafito">
            <tr>
              <th className="px-4 py-2 font-medium">Producto</th>
              <th className="px-4 py-2 font-medium">SKU</th>
              <th className="px-4 py-2 text-right font-medium">Venta</th>
              <th className="px-4 py-2 text-right font-medium">Margen</th>
              <th className="px-4 py-2 text-right font-medium">Stock</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-niebla">
            {loading ? (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-grafito">
                  Cargando…
                </td>
              </tr>
            ) : products.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-grafito">
                  No hay productos. Créalos desde la API o el panel de admin.
                </td>
              </tr>
            ) : (
              products.map((p) => (
                <tr key={p.id} className={p.stock_bajo ? "bg-achiote/5" : undefined}>
                  <td className="px-4 py-2 text-tinta">{p.nombre}</td>
                  <td className="px-4 py-2 text-grafito">{p.sku}</td>
                  <td className="tabular px-4 py-2 text-right text-tinta">
                    {formatCOP(p.precio_venta_centavos)}
                  </td>
                  <td className="tabular px-4 py-2 text-right text-grafito">
                    {p.margen_bps === null ? "—" : `${(p.margen_bps / 100).toFixed(1)}%`}
                  </td>
                  <td className="tabular px-4 py-2 text-right text-tinta">
                    {formatCantidad(p.stock_milesimas)}
                    {p.stock_bajo && <span className="ml-1 text-achiote">●</span>}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
