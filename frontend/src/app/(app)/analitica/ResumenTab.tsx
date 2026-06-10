"use client";

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

import { formatCOP } from "@/lib/money";
import type {
  AnalyticsSummary,
  ByMethodRow,
  Granularidad,
  TimeSeriesPoint,
  TopProduct,
} from "@/lib/types";

import {
  BotonCsv,
  deltaTexto,
  Estado,
  Kpi,
  MARCA,
  Panel,
  type Rango,
  exportarCsv,
  getRango,
  useFetch,
} from "./_ui";

const ejeY = (v: unknown) => formatCOP(Number(v) * 100);

export default function ResumenTab({ rango, gran }: { rango: Rango; gran: Granularidad }) {
  const f = useFetch(
    async () => {
      const [summary, serie, top, metodos] = await Promise.all([
        getRango<AnalyticsSummary>("analytics/summary", rango),
        getRango<TimeSeriesPoint[]>("analytics/timeseries", rango, `&granularidad=${gran}`),
        getRango<TopProduct[]>("analytics/top-products", rango, "&limit=8"),
        getRango<ByMethodRow[]>("analytics/by-method", rango),
      ]);
      return { summary, serie, top, metodos };
    },
    [rango.desde, rango.hasta, gran],
  );

  return (
    <Estado fetch={f} vacio={f.data?.summary.n_transacciones === 0}>
      {f.data && (
        <>
          <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Kpi
              label="Ventas"
              valor={formatCOP(f.data.summary.ventas_centavos)}
              delta={deltaTexto(f.data.summary.comparativa?.delta_ventas_bps ?? null)}
            />
            <Kpi
              label="Transacciones"
              valor={String(f.data.summary.n_transacciones)}
              delta={deltaTexto(f.data.summary.comparativa?.delta_transacciones_bps ?? null)}
            />
            <Kpi
              label="Ticket promedio"
              valor={formatCOP(f.data.summary.ticket_promedio_centavos)}
              delta={deltaTexto(f.data.summary.comparativa?.delta_ticket_bps ?? null)}
            />
            <Kpi
              label="Margen"
              valor={formatCOP(f.data.summary.margen_centavos)}
              sub={
                f.data.summary.margen_bps !== null
                  ? `${(f.data.summary.margen_bps / 100).toFixed(1)}%`
                  : undefined
              }
              delta={deltaTexto(f.data.summary.comparativa?.delta_margen_bps ?? null)}
            />
          </div>

          <Panel
            titulo="Ventas en el tiempo"
            acciones={<BotonCsv onClick={() => exportarCsv("timeseries", rango, gran)} />}
          >
            <ResponsiveContainer width="100%" height={260}>
              <LineChart
                data={f.data.serie.map((p) => ({ periodo: p.periodo, ventas: p.ventas_centavos / 100 }))}
                margin={{ top: 8, right: 12, left: 4, bottom: 4 }}
              >
                <CartesianGrid stroke="#e4e1da" vertical={false} />
                <XAxis dataKey="periodo" tick={{ fontSize: 11, fill: "#5c5f66" }} minTickGap={24} />
                <YAxis tick={{ fontSize: 11, fill: "#5c5f66" }} width={70} tickFormatter={ejeY} />
                <Tooltip formatter={ejeY} />
                <Line type="monotone" dataKey="ventas" stroke={MARCA} strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </Panel>

          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <Panel
              titulo="Productos top"
              acciones={<BotonCsv onClick={() => exportarCsv("top-products", rango)} />}
            >
              <table className="w-full text-sm">
                <tbody className="divide-y divide-niebla">
                  {f.data.top.map((t) => (
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
                <BarChart
                  data={f.data.metodos.map((m) => ({ metodo: m.metodo, ventas: m.ventas_centavos / 100 }))}
                  margin={{ top: 8, right: 12, left: 4, bottom: 4 }}
                >
                  <CartesianGrid stroke="#e4e1da" vertical={false} />
                  <XAxis dataKey="metodo" tick={{ fontSize: 11, fill: "#5c5f66" }} />
                  <YAxis tick={{ fontSize: 11, fill: "#5c5f66" }} width={70} tickFormatter={ejeY} />
                  <Tooltip formatter={ejeY} />
                  <Bar dataKey="ventas" fill={MARCA} radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </Panel>
          </div>
        </>
      )}
    </Estado>
  );
}
