"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { apiGet } from "@/lib/api";
import { formatCantidad, formatCOP } from "@/lib/money";
import type { Product, UserMe } from "@/lib/types";

export default function InventarioPage() {
  const router = useRouter();
  const [products, setProducts] = useState<Product[]>([]);
  const [alertas, setAlertas] = useState<Product[]>([]);
  const [q, setQ] = useState("");
  const [role, setRole] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiGet<UserMe>("auth/me")
      .then((u) => setRole(u.role))
      .catch(() => setRole(null));
  }, []);

  useEffect(() => {
    let cancel = false;
    (async () => {
      const [list, low] = await Promise.all([
        apiGet<Product[]>(`products?q=${encodeURIComponent(q)}&solo_activos=false&limit=100`).catch(
          () => [],
        ),
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

  const esAdmin = role === "admin";

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-2xl font-bold text-tinta">Inventario</h1>
        <div className="flex flex-wrap items-center gap-2">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Buscar…"
            className="h-10 w-48 rounded-lg border border-niebla px-3 text-sm"
          />
          {esAdmin && (
            <>
              <Link href="/inventario/proveedores" className="rounded-md border border-niebla px-3 py-2 text-sm font-medium text-tinta transition hover:bg-niebla/60">
                Proveedores
              </Link>
              <Link href="/inventario/entradas" className="rounded-md border border-niebla px-3 py-2 text-sm font-medium text-tinta transition hover:bg-niebla/60">
                Entrada de mercancía
              </Link>
              <Link href="/inventario/nuevo" className="rounded-md bg-achiote px-3 py-2 text-sm font-semibold text-papel transition hover:brightness-105">
                Nuevo producto
              </Link>
            </>
          )}
        </div>
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
                  No hay productos. {esAdmin && "Crea el primero con “Nuevo producto”."}
                </td>
              </tr>
            ) : (
              products.map((p) => (
                <tr
                  key={p.id}
                  onClick={esAdmin ? () => router.push(`/inventario/${p.id}`) : undefined}
                  className={`${p.stock_bajo ? "bg-achiote/5" : ""} ${
                    esAdmin ? "cursor-pointer hover:bg-niebla/30" : ""
                  } ${!p.activo ? "opacity-50" : ""}`}
                >
                  <td className="px-4 py-2 text-tinta">
                    {p.nombre}
                    {!p.activo && <span className="ml-1 text-xs text-grafito">(inactivo)</span>}
                  </td>
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
