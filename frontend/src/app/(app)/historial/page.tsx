"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ApiError, apiGet, apiPost } from "@/lib/api";
import { dianBadge, type DianTone, puedeEmitir } from "@/lib/fiscal";
import { formatCOP } from "@/lib/money";
import type { FiscalEmissionRead, InvoiceRead, UserMe } from "@/lib/types";

const TONE_CLASS: Record<DianTone, string> = {
  neutral: "bg-niebla/60 text-grafito",
  info: "bg-azulon/10 text-azulon",
  ok: "bg-green-100 text-green-800",
  error: "bg-achiote/15 text-achiote",
};

export default function HistorialPage() {
  const [invoices, setInvoices] = useState<InvoiceRead[]>([]);
  const [role, setRole] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [emitiendo, setEmitiendo] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancel = false;
    (async () => {
      const [inv, me] = await Promise.all([
        apiGet<InvoiceRead[]>("invoices?limit=100").catch(() => []),
        apiGet<UserMe>("auth/me").catch(() => null),
      ]);
      if (cancel) return;
      setInvoices(inv);
      setRole(me?.role ?? null);
      setLoading(false);
    })();
    return () => {
      cancel = true;
    };
  }, []);

  async function emitir(invoiceId: number) {
    setEmitiendo(invoiceId);
    setError(null);
    try {
      const em = await apiPost<FiscalEmissionRead>(`fiscal/invoices/${invoiceId}/emit`);
      setInvoices((prev) =>
        prev.map((inv) =>
          inv.id === invoiceId ? { ...inv, dian_status: em.status, cufe: em.cufe } : inv,
        ),
      );
      if (em.status === "rejected") {
        setError(`Factura ${invoiceId} rechazada: ${em.motivo_rechazo ?? "sin detalle"}`);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo emitir.");
    } finally {
      setEmitiendo(null);
    }
  }

  const esAdmin = role === "admin";

  return (
    <div>
      <h1 className="font-display text-2xl font-bold text-tinta">Historial de facturas</h1>

      <p className="mt-2 rounded-lg border border-niebla bg-niebla/30 px-3 py-2 text-xs text-grafito">
        La emisión electrónica real requiere la habilitación del comercio ante la DIAN
        (Resolución 165/2023) y un Proveedor Tecnológico autorizado. En modo demostración los
        documentos son simulados y <strong>no tienen validez fiscal</strong>.
      </p>

      {error && (
        <div role="alert" className="mt-3 rounded-lg border border-achiote/30 bg-achiote/10 px-3 py-2 text-sm text-achiote">
          {error}
        </div>
      )}

      <div className="mt-4 overflow-hidden rounded-2xl border border-niebla bg-white">
        <table className="w-full text-sm">
          <thead className="border-b border-niebla bg-niebla/30 text-left text-grafito">
            <tr>
              <th className="px-4 py-2 font-medium">Factura</th>
              <th className="px-4 py-2 font-medium">Fecha</th>
              <th className="px-4 py-2 font-medium">Pago</th>
              <th className="px-4 py-2 text-right font-medium">Total</th>
              <th className="px-4 py-2 font-medium">DIAN</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-niebla">
            {loading ? (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-grafito">
                  Cargando…
                </td>
              </tr>
            ) : invoices.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-grafito">
                  Aún no hay ventas registradas.
                </td>
              </tr>
            ) : (
              invoices.map((inv) => {
                const badge = dianBadge(inv.dian_status);
                return (
                  <tr key={inv.id}>
                    <td className="tabular px-4 py-2 font-medium text-tinta">
                      <Link href={`/historial/${inv.sale_id}`} className="text-azulon hover:underline">
                        {inv.numero_completo}
                      </Link>
                      {inv.cufe && (
                        <span className="tabular block max-w-[10rem] truncate text-[10px] text-grafito">
                          CUFE {inv.cufe}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2 text-grafito">
                      {new Date(inv.created_at).toLocaleString("es-CO")}
                    </td>
                    <td className="px-4 py-2 capitalize text-grafito">{inv.metodo_pago}</td>
                    <td className="tabular px-4 py-2 text-right text-tinta">
                      {formatCOP(inv.total_centavos)}
                    </td>
                    <td className="px-4 py-2">
                      <span
                        className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${TONE_CLASS[badge.tone]}`}
                      >
                        {badge.text}
                      </span>
                      {esAdmin && puedeEmitir(inv.dian_status) && (
                        <button
                          onClick={() => emitir(inv.id)}
                          disabled={emitiendo === inv.id}
                          className="ml-2 rounded-md border border-azulon/40 px-2 py-0.5 text-xs font-medium text-azulon transition hover:bg-azulon/10 disabled:opacity-60"
                        >
                          {emitiendo === inv.id ? "Emitiendo…" : "Emitir a DIAN"}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
