"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { apiGet } from "@/lib/api";
import { formatCOP } from "@/lib/money";
import { type Preset, rangoDePreset } from "@/lib/rango";
import type {
  AnalyticsSummary,
  ByMethodRow,
  Granularidad,
  InventoryStats,
  TimeSeriesPoint,
  TopProduct,
} from "@/lib/types";

const PRESETS: { key: Preset; label: string; gran: Granularidad }[] = [
  { key: "7d", label: "7 días", gran: "dia" },
  { key: "30d", label: "30 días", gran: "dia" },
  { key: "mes", label: "Este mes", gran: "dia" },
  { key: "ano", label: "Este año", gran: "mes" },
];

function deltaTexto(bps: number | null): { texto: string; positivo: boolean } | null {
  if (bps === null) return null;
  return { texto: `${bps >= 0 ? "+" : ""}${(bps / 100).toFixed(1)}%`, positivo: bps >= 0 };
}

export default function AnaliticaPage() {
  const [preset, setPreset] = useState<Preset>("30d");
  const [gran, setGran] = useState<Granularidad>("dia");
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [serie, setSerie] = useState<TimeSeriesPoint[]>([]);
  const [top, setTop] = useState<TopProduct[]>([]);
  const [metodos, setMetodos] = useState<ByMethodRow[]>([]);
  const [inv, setInv] = useState<InventoryStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [denegado, setDenegado] = useState(false);

  useEffect(() => {
    const { desde, hasta } = rangoDePreset(preset, new Date());
    const q = `desde=${desde}&hasta=${hasta}`;
    let cancel = false;
    (async () => {
      try {
        const [s, ts, tp, bm, iv] = await Promise.all([
          apiGet<AnalyticsSummary>(`analytics/summary?${q}`),
          apiGet<TimeSeriesPoint[]>(`analytics/timeseries?${q}&granularidad=${gran}`),
          apiGet<TopProduct[]>(`analytics/top-products?${q}&limit=8`),
          apiGet<ByMethodRow[]>(`analytics/by-method?${q}`),
          apiGet<InventoryStats>(`analytics/inventory?${q}`),
        ]);
        if (cancel) return;
        setSummary(s);
        setSerie(ts);
        setTop(tp);
        setMetodos(bm);
        setInv(iv);
      } catch {
        if (!cancel) setDenegado(true);
      } finally {
        if (!cancel) setLoading(false);
      }
    })();
    return () => {
      cancel = true;
    };
  }, [preset, gran]);

  function exportar() {
    const { desde, hasta } = rangoDePreset(preset, new Date());
    window.location.href = `/api/proxy/analytics/export.csv?dataset=timeseries&desde=${desde}&hasta=${hasta}&granularidad=${gran}`;
  }

  if (denegado) {
    return <p className="text-grafito">Esta sección es solo para administradores.</p>;
  }

  const serieData = serie.map((p) => ({ periodo: p.periodo, ventas: p.ventas_centavos / 100 }));
  const metodoData = metodos.map((m) => ({ metodo: m.metodo, ventas: m.ventas_centavos / 100 }));

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-2xl font-bold text-tinta">Analítica</h1>
        <div className="flex flex-wrap items-center gap-2">
          {PRESETS.map((pr) => (
            <button
              key={pr.key}
              onClick={() => {
                setPreset(pr.key);
                setGran(pr.gran);
              }}
              aria-pressed={preset === pr.key}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
                preset === pr.key
                  ? "bg-azulon/10 text-azulon"
                  : "text-grafito hover:bg-niebla/60"
              }`}
            >
              {pr.label}
            </button>
          ))}
          <button
            onClick={exportar}
            className="rounded-md border border-niebla px-3 py-1.5 text-sm font-medium text-tinta transition hover:bg-niebla/60"
          >
            Exportar CSV
          </button>
        </div>
      </div>

      {loading || !summary ? (
        <p className="mt-6 text-grafito">Cargando…</p>
      ) : (
        <>
          <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Kpi
              label="Ventas"
              valor={formatCOP(summary.ventas_centavos)}
              delta={deltaTexto(summary.comparativa?.delta_ventas_bps ?? null)}
            />
            <Kpi
              label="Transacciones"
              valor={String(summary.n_transacciones)}
              delta={deltaTexto(summary.comparativa?.delta_transacciones_bps ?? null)}
            />
            <Kpi
              label="Ticket promedio"
              valor={formatCOP(summary.ticket_promedio_centavos)}
              delta={deltaTexto(summary.comparativa?.delta_ticket_bps ?? null)}
            />
            <Kpi
              label="Margen"
              valor={formatCOP(summary.margen_centavos)}
              sub={summary.margen_bps !== null ? `${(summary.margen_bps / 100).toFixed(1)}%` : "—"}
              delta={deltaTexto(summary.comparativa?.delta_margen_bps ?? null)}
            />
          </div>

          <Panel titulo="Ventas en el tiempo">
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={serieData} margin={{ top: 8, right: 12, left: 4, bottom: 4 }}>
                <CartesianGrid stroke="#e4e1da" vertical={false} />
                <XAxis dataKey="periodo" tick={{ fontSize: 11, fill: "#5c5f66" }} minTickGap={24} />
                <YAxis tick={{ fontSize: 11, fill: "#5c5f66" }} width={70}
                  tickFormatter={(v) => formatCOP(Number(v) * 100)} />
                <Tooltip formatter={(v) => formatCOP(Number(v) * 100)} />
                <Line type="monotone" dataKey="ventas" stroke="#173f8a" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </Panel>

          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <Panel titulo="Productos top">
              <table className="w-full text-sm">
                <tbody className="divide-y divide-niebla">
                  {top.map((t) => (
                    <tr key={t.product_id}>
                      <td className="py-1.5 text-tinta">{t.nombre}</td>
                      <td className="tabular py-1.5 text-right text-tinta">
                        {formatCOP(t.ventas_centavos)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Panel>

            <Panel titulo="Ventas por método">
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={metodoData} margin={{ top: 8, right: 12, left: 4, bottom: 4 }}>
                  <CartesianGrid stroke="#e4e1da" vertical={false} />
                  <XAxis dataKey="metodo" tick={{ fontSize: 11, fill: "#5c5f66" }} />
                  <YAxis tick={{ fontSize: 11, fill: "#5c5f66" }} width={70}
                    tickFormatter={(v) => formatCOP(Number(v) * 100)} />
                  <Tooltip formatter={(v) => formatCOP(Number(v) * 100)} />
                  <Bar dataKey="ventas" fill="#173f8a" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </Panel>
          </div>

          {inv && (
            <Panel titulo="Inventario">
              <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                <Kpi label="Stock valorizado" valor={formatCOP(inv.stock_valorizado_centavos)} />
                <Kpi label="COGS del periodo" valor={formatCOP(inv.cogs_periodo_centavos)} />
                <Kpi
                  label="Rotación"
                  valor={inv.rotacion_bps !== null ? `${(inv.rotacion_bps / 100).toFixed(1)}%` : "—"}
                />
                <Kpi label="Productos en stock bajo" valor={String(inv.n_stock_bajo)} />
              </div>
            </Panel>
          )}
        </>
      )}
    </div>
  );
}

function Kpi({
  label,
  valor,
  sub,
  delta,
}: {
  label: string;
  valor: string;
  sub?: string;
  delta?: { texto: string; positivo: boolean } | null;
}) {
  return (
    <div className="rounded-xl border border-niebla bg-white p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-grafito">{label}</p>
      <p className="tabular mt-1 text-2xl font-bold text-tinta">{valor}</p>
      <div className="mt-1 flex items-center gap-2 text-xs">
        {sub && <span className="text-grafito">{sub}</span>}
        {delta && (
          <span className={delta.positivo ? "text-green-700" : "text-achiote"}>{delta.texto}</span>
        )}
      </div>
    </div>
  );
}

function Panel({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <section className="mt-4 rounded-2xl border border-niebla bg-white p-4">
      <h2 className="mb-2 font-display text-sm font-bold uppercase tracking-wide text-grafito">
        {titulo}
      </h2>
      {children}
    </section>
  );
}
