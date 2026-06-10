"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { ApiError, apiGet, apiPost } from "@/lib/api";
import { dianBadge, type DianTone, puedeEmitir } from "@/lib/fiscal";
import { formatCantidad, formatCOP } from "@/lib/money";
import type { FiscalEmissionRead, SaleRead, UserMe } from "@/lib/types";

const TONE: Record<DianTone, string> = {
  neutral: "bg-niebla/60 text-grafito",
  info: "bg-azulon/10 text-azulon",
  ok: "bg-green-100 text-green-800",
  error: "bg-achiote/15 text-achiote",
};

export default function VentaDetallePage() {
  const params = useParams();
  const id = Number(params.id);
  const [sale, setSale] = useState<SaleRead | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [emitiendo, setEmitiendo] = useState(false);

  const cargar = useCallback(async () => {
    setSale(await apiGet<SaleRead>(`sales/${id}`));
  }, [id]);

  useEffect(() => {
    apiGet<UserMe>("auth/me").then((u) => setRole(u.role)).catch(() => setRole(null));
  }, []);

  useEffect(() => {
    let cancel = false;
    (async () => {
      try {
        await cargar();
      } catch {
        if (!cancel) setError("No se pudo cargar la venta.");
      } finally {
        if (!cancel) setLoading(false);
      }
    })();
    return () => {
      cancel = true;
    };
  }, [cargar]);

  async function emitir() {
    if (!sale?.invoice) return;
    setEmitiendo(true);
    setError(null);
    try {
      const em = await apiPost<FiscalEmissionRead>(`fiscal/invoices/${sale.invoice.id}/emit`);
      await cargar();
      if (em.status === "rejected") setError(`Rechazada: ${em.motivo_rechazo ?? "sin detalle"}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo emitir.");
    } finally {
      setEmitiendo(false);
    }
  }

  if (loading) return <p className="text-grafito">Cargando…</p>;
  if (!sale) return <p className="text-grafito">{error ?? "Venta no encontrada."}</p>;

  const inv = sale.invoice;
  const badge = inv ? dianBadge(inv.dian_status) : null;

  return (
    <div className="mx-auto max-w-2xl">
      <Link href="/historial" className="text-sm text-azulon hover:underline">
        ← Historial
      </Link>
      <h1 className="mt-2 font-display text-2xl font-bold text-tinta">
        Venta #{sale.id}
        {inv && <span className="tabular ml-2 text-base font-normal text-grafito">{inv.numero_completo}</span>}
      </h1>

      {error && (
        <div role="alert" className="mt-3 rounded-lg border border-achiote/30 bg-achiote/10 px-3 py-2 text-sm text-achiote">
          {error}
        </div>
      )}

      <section className="mt-4 overflow-hidden rounded-2xl border border-niebla bg-white">
        <table className="w-full text-sm">
          <thead className="border-b border-niebla bg-niebla/30 text-left text-grafito">
            <tr>
              <th className="px-4 py-2 font-medium">Producto</th>
              <th className="px-4 py-2 text-right font-medium">Cant.</th>
              <th className="px-4 py-2 text-right font-medium">Precio</th>
              <th className="px-4 py-2 text-right font-medium">IVA</th>
              <th className="px-4 py-2 text-right font-medium">Total</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-niebla">
            {sale.items.map((it) => (
              <tr key={it.id}>
                <td className="px-4 py-2 text-tinta">{it.nombre_snapshot}</td>
                <td className="tabular px-4 py-2 text-right text-grafito">
                  {formatCantidad(it.cantidad_milesimas)}
                </td>
                <td className="tabular px-4 py-2 text-right text-grafito">
                  {formatCOP(it.precio_unitario_centavos)}
                </td>
                <td className="tabular px-4 py-2 text-right text-grafito">
                  {formatCOP(it.iva_centavos)}
                </td>
                <td className="tabular px-4 py-2 text-right text-tinta">
                  {formatCOP(it.total_linea_centavos)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="mt-4 grid gap-4 sm:grid-cols-2">
        <dl className="rounded-2xl border border-niebla bg-white p-4 text-sm">
          <Row label="Subtotal" value={formatCOP(sale.subtotal_centavos)} />
          <Row label="IVA" value={formatCOP(sale.iva_total_centavos)} />
          <Row label="Total" value={formatCOP(sale.total_centavos)} fuerte />
          <Row label="Método de pago" value={sale.metodo_pago ?? "—"} />
          <Row label="Estado venta" value={sale.status} />
        </dl>

        <div className="rounded-2xl border border-niebla bg-white p-4 text-sm">
          <h2 className="mb-2 text-xs font-bold uppercase tracking-wide text-grafito">Factura / DIAN</h2>
          {inv ? (
            <>
              <Row label="Número" value={inv.numero_completo} />
              <div className="flex items-center justify-between py-1">
                <dt className="text-grafito">Estado DIAN</dt>
                <dd>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${TONE[badge!.tone]}`}>
                    {badge!.text}
                  </span>
                </dd>
              </div>
              {inv.cufe && (
                <p className="tabular mt-1 break-all text-[10px] text-grafito">CUFE {inv.cufe}</p>
              )}
              {role === "admin" && puedeEmitir(inv.dian_status) && (
                <button
                  onClick={emitir}
                  disabled={emitiendo}
                  className="mt-3 h-10 w-full rounded-lg border border-azulon/40 text-sm font-medium text-azulon transition hover:bg-azulon/10 disabled:opacity-60"
                >
                  {emitiendo ? "Emitiendo…" : "Emitir a DIAN"}
                </button>
              )}
              <p className="mt-3 text-[11px] text-grafito">
                La emisión real requiere habilitación del comercio ante la DIAN. En demo, sin
                validez fiscal.
              </p>
            </>
          ) : (
            <p className="text-grafito">Esta venta aún no tiene factura (pago pendiente o rechazado).</p>
          )}
        </div>
      </section>
    </div>
  );
}

function Row({ label, value, fuerte }: { label: string; value: string; fuerte?: boolean }) {
  return (
    <div className={`flex justify-between py-1 ${fuerte ? "font-bold text-tinta" : ""}`}>
      <dt className="text-grafito">{label}</dt>
      <dd className={fuerte ? "tabular text-tinta" : "tabular capitalize text-tinta"}>{value}</dd>
    </div>
  );
}
