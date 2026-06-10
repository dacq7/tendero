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
import type { GrowthPoint, Projection, TicketBucket } from "@/lib/types";

import {
  BotonCsv,
  Estado,
  Kpi,
  MARCA,
  Panel,
  type Rango,
  deltaTexto,
  exportarCsv,
  getRango,
  useFetch,
} from "./_ui";

const DOW = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];
const ejeY = (v: unknown) => formatCOP(Number(v) * 100);

/** Resta ~18 meses a una fecha YYYY-MM-DD para que YoY tenga base histórica. */
function hace18Meses(hasta: string): string {
  const d = new Date(`${hasta}T00:00:00`);
  d.setMonth(d.getMonth() - 18);
  return d.toISOString().slice(0, 10);
}

export default function TendenciasTab({ rango }: { rango: Rango }) {
  // Crecimiento: ventana ancha fija (18 meses) → MoM y YoY con historia.
  const rangoAncho: Rango = { desde: hace18Meses(rango.hasta), hasta: rango.hasta };
  const f = useFetch(
    async () => {
      const [growth, porHora, porDia, proyeccion] = await Promise.all([
        getRango<GrowthPoint[]>("analytics/growth", rangoAncho),
        getRango<TicketBucket[]>("analytics/ticket-by-hour", rango),
        getRango<TicketBucket[]>("analytics/ticket-by-dow", rango),
        getRango<Projection>("analytics/projection", rango),
      ]);
      return { growth, porHora, porDia, proyeccion };
    },
    [rango.desde, rango.hasta],
  );

  const ultimo = f.data?.growth.at(-1);

  return (
    <Estado fetch={f} vacio={f.data?.growth.length === 0}>
      {f.data && (
        <>
          <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Kpi
              label="Crecimiento mensual (MoM)"
              valor={ultimo ? formatCOP(ultimo.ventas_centavos) : "—"}
              sub="último mes"
              delta={deltaTexto(ultimo?.mom_bps ?? null)}
            />
            <Kpi
              label="Vs. año anterior (YoY)"
              valor={
                ultimo?.yoy_bps != null
                  ? `${ultimo.yoy_bps >= 0 ? "+" : ""}${(ultimo.yoy_bps / 100).toFixed(1)}%`
                  : "Sin base"
              }
              sub={ultimo?.yoy_bps == null ? "falta historia del año previo" : "mismo mes, año pasado"}
            />
            <Kpi
              label="Ventas del periodo"
              valor={formatCOP(f.data.proyeccion.ventas_actual_centavos)}
              sub={`${f.data.proyeccion.dias_transcurridos}/${f.data.proyeccion.dias_periodo} días`}
            />
            <Kpi
              label={f.data.proyeccion.es_estimacion ? "Proyección (estimada)" : "Cierre del periodo"}
              valor={formatCOP(f.data.proyeccion.ventas_proyectada_centavos)}
              sub={f.data.proyeccion.es_estimacion ? "tendencia, no es promesa" : "periodo cerrado"}
            />
          </div>

          <Panel
            titulo="Crecimiento mensual (18 meses)"
            acciones={<BotonCsv onClick={() => exportarCsv("growth", rangoAncho)} />}
          >
            <ResponsiveContainer width="100%" height={260}>
              <LineChart
                data={f.data.growth.map((g) => ({
                  periodo: g.periodo.slice(0, 7),
                  ventas: g.ventas_centavos / 100,
                  margen: g.margen_centavos / 100,
                }))}
                margin={{ top: 8, right: 12, left: 4, bottom: 4 }}
              >
                <CartesianGrid stroke="#e4e1da" vertical={false} />
                <XAxis dataKey="periodo" tick={{ fontSize: 11, fill: "#5c5f66" }} minTickGap={20} />
                <YAxis tick={{ fontSize: 11, fill: "#5c5f66" }} width={70} tickFormatter={ejeY} />
                <Tooltip formatter={ejeY} />
                <Line type="monotone" dataKey="ventas" name="Ventas" stroke={MARCA} strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="margen" name="Margen" stroke="#1f7a4d" strokeWidth={1.5} strokeDasharray="4 3" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </Panel>

          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <Panel titulo="Ticket por hora del día">
              <ResponsiveContainer width="100%" height={220}>
                <BarChart
                  data={f.data.porHora.map((b) => ({ hora: `${b.bucket}h`, ticket: b.ticket_promedio_centavos / 100 }))}
                  margin={{ top: 8, right: 12, left: 4, bottom: 4 }}
                >
                  <CartesianGrid stroke="#e4e1da" vertical={false} />
                  <XAxis dataKey="hora" tick={{ fontSize: 10, fill: "#5c5f66" }} minTickGap={8} />
                  <YAxis tick={{ fontSize: 11, fill: "#5c5f66" }} width={70} tickFormatter={ejeY} />
                  <Tooltip formatter={ejeY} />
                  <Bar dataKey="ticket" fill={MARCA} radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </Panel>

            <Panel titulo="Ticket por día de la semana">
              <ResponsiveContainer width="100%" height={220}>
                <BarChart
                  data={f.data.porDia.map((b) => ({ dia: DOW[b.bucket] ?? b.bucket, ticket: b.ticket_promedio_centavos / 100 }))}
                  margin={{ top: 8, right: 12, left: 4, bottom: 4 }}
                >
                  <CartesianGrid stroke="#e4e1da" vertical={false} />
                  <XAxis dataKey="dia" tick={{ fontSize: 11, fill: "#5c5f66" }} />
                  <YAxis tick={{ fontSize: 11, fill: "#5c5f66" }} width={70} tickFormatter={ejeY} />
                  <Tooltip formatter={ejeY} />
                  <Bar dataKey="ticket" fill={MARCA} radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </Panel>
          </div>
        </>
      )}
    </Estado>
  );
}
