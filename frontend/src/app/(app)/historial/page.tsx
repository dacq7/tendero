"use client";

import { useEffect, useState } from "react";

import { apiGet } from "@/lib/api";
import { formatCOP } from "@/lib/money";
import type { InvoiceRead } from "@/lib/types";

export default function HistorialPage() {
  const [invoices, setInvoices] = useState<InvoiceRead[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiGet<InvoiceRead[]>("invoices?limit=100")
      .then(setInvoices)
      .catch(() => setInvoices([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1 className="font-display text-2xl font-bold text-tinta">Historial de facturas</h1>
      <div className="mt-4 overflow-hidden rounded-2xl border border-niebla bg-white">
        <table className="w-full text-sm">
          <thead className="border-b border-niebla bg-niebla/30 text-left text-grafito">
            <tr>
              <th className="px-4 py-2 font-medium">Factura</th>
              <th className="px-4 py-2 font-medium">Fecha</th>
              <th className="px-4 py-2 font-medium">Pago</th>
              <th className="px-4 py-2 text-right font-medium">Total</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-niebla">
            {loading ? (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-grafito">
                  Cargando…
                </td>
              </tr>
            ) : invoices.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-grafito">
                  Aún no hay ventas registradas.
                </td>
              </tr>
            ) : (
              invoices.map((inv) => (
                <tr key={inv.id}>
                  <td className="tabular px-4 py-2 font-medium text-tinta">
                    {inv.numero_completo}
                  </td>
                  <td className="px-4 py-2 text-grafito">
                    {new Date(inv.created_at).toLocaleString("es-CO")}
                  </td>
                  <td className="px-4 py-2 capitalize text-grafito">{inv.metodo_pago}</td>
                  <td className="tabular px-4 py-2 text-right text-tinta">
                    {formatCOP(inv.total_centavos)}
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
