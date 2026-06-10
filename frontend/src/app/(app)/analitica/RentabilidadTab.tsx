"use client";

import {
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";

import { formatCantidad, formatCOP } from "@/lib/money";
import type { Cuadrante, ProfitCategory, ProfitMatrix, ProfitProduct } from "@/lib/types";

import {
  ACCION,
  BotonCsv,
  Estado,
  GRAFITO,
  MARCA,
  Panel,
  type Rango,
  VERDE,
  exportarCsv,
  formatPct,
  getRango,
  useFetch,
} from "./_ui";

// Color e etiqueta por cuadrante de la matriz volumen × margen.
const CUADRANTE: Record<Cuadrante, { color: string; label: string }> = {
  estrella: { color: VERDE, label: "Estrella (vende y deja)" },
  tiron: { color: MARCA, label: "Tirón (vende, poco margen)" },
  nicho: { color: "#b8860b", label: "Nicho (margen, poco volumen)" },
  perro: { color: ACCION, label: "Perro (poco volumen y margen)" },
};

export default function RentabilidadTab({ rango }: { rango: Rango }) {
  const f = useFetch(
    async () => {
      const [productos, categorias, matriz] = await Promise.all([
        getRango<ProfitProduct[]>("analytics/profit-products", rango),
        getRango<ProfitCategory[]>("analytics/profit-categories", rango),
        getRango<ProfitMatrix>("analytics/profit-matrix", rango),
      ]);
      return { productos, categorias, matriz };
    },
    [rango.desde, rango.hasta],
  );

  const puntos =
    f.data?.matriz.items.map((i) => ({
      x: i.volumen_milesimas / 1000,
      y: i.margen_bps ?? 0,
      z: i.ventas_centavos,
      nombre: i.nombre,
      cuadrante: i.cuadrante,
    })) ?? [];

  return (
    <Estado fetch={f} vacio={f.data?.productos.length === 0}>
      {f.data && (
        <>
          <Panel
            titulo="Matriz volumen × margen — estrellas y perros"
            acciones={<BotonCsv onClick={() => exportarCsv("profit-products", rango)} />}
          >
            <p className="mb-2 text-xs text-grafito">
              Cada punto es un producto. Eje X: unidades vendidas. Eje Y: margen (%). Las líneas
              son las medianas: arriba-derecha son tus <strong className="text-tinta">estrellas</strong>;
              abajo-izquierda, los <strong className="text-tinta">perros</strong>.
            </p>
            <ResponsiveContainer width="100%" height={320}>
              <ScatterChart margin={{ top: 8, right: 16, left: 4, bottom: 16 }}>
                <CartesianGrid stroke="#e4e1da" />
                <XAxis
                  type="number"
                  dataKey="x"
                  name="Volumen"
                  tick={{ fontSize: 11, fill: GRAFITO }}
                  tickFormatter={(v) => formatCantidad(Number(v) * 1000)}
                  label={{ value: "Unidades vendidas", position: "insideBottom", offset: -8, fontSize: 11, fill: GRAFITO }}
                />
                <YAxis
                  type="number"
                  dataKey="y"
                  name="Margen"
                  tick={{ fontSize: 11, fill: GRAFITO }}
                  tickFormatter={(v) => `${(Number(v) / 100).toFixed(0)}%`}
                  width={48}
                />
                <ZAxis type="number" dataKey="z" range={[40, 400]} name="Ventas" />
                <ReferenceLine x={f.data.matriz.umbral_volumen_milesimas / 1000} stroke="#c9c6bf" />
                <ReferenceLine y={f.data.matriz.umbral_margen_bps} stroke="#c9c6bf" />
                <Tooltip
                  cursor={{ strokeDasharray: "3 3" }}
                  formatter={(value, name) => {
                    if (name === "Margen") return [`${(Number(value) / 100).toFixed(1)}%`, name];
                    if (name === "Ventas") return [formatCOP(Number(value)), name];
                    return [formatCantidad(Number(value) * 1000), name];
                  }}
                  labelFormatter={() => ""}
                  content={({ payload }) => {
                    const p = payload?.[0]?.payload;
                    if (!p) return null;
                    return (
                      <div className="rounded-lg border border-niebla bg-white px-3 py-2 text-xs shadow-sm">
                        <p className="font-semibold text-tinta">{p.nombre}</p>
                        <p className="tabular text-grafito">{formatCantidad(p.x * 1000)} und · {(p.y / 100).toFixed(1)}%</p>
                        <p className="tabular text-grafito">{formatCOP(p.z)}</p>
                      </div>
                    );
                  }}
                />
                <Scatter data={puntos}>
                  {puntos.map((p, i) => (
                    <Cell key={i} fill={CUADRANTE[p.cuadrante as Cuadrante].color} />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-grafito">
              {Object.values(CUADRANTE).map((c) => (
                <span key={c.label} className="flex items-center gap-1.5">
                  <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: c.color }} />
                  {c.label}
                </span>
              ))}
            </div>
          </Panel>

          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <Panel titulo="Rentabilidad por producto">
              <TablaContribucion
                filas={f.data.productos.slice(0, 12).map((p) => ({
                  clave: p.product_id,
                  nombre: p.nombre,
                  margen: p.margen_centavos,
                  margen_bps: p.margen_bps,
                  contribucion_bps: p.contribucion_bps,
                }))}
              />
            </Panel>
            <Panel
              titulo="Rentabilidad por categoría"
              acciones={<BotonCsv onClick={() => exportarCsv("profit-categories", rango)} />}
            >
              <TablaContribucion
                filas={f.data.categorias.map((c) => ({
                  clave: c.categoria,
                  nombre: c.categoria,
                  margen: c.margen_centavos,
                  margen_bps: c.margen_bps,
                  contribucion_bps: c.contribucion_bps,
                }))}
              />
            </Panel>
          </div>
        </>
      )}
    </Estado>
  );
}

function TablaContribucion({
  filas,
}: {
  filas: {
    clave: string | number;
    nombre: string;
    margen: number;
    margen_bps: number | null;
    contribucion_bps: number | null;
  }[];
}) {
  return (
    <table className="w-full text-sm">
      <thead className="text-left text-xs uppercase tracking-wide text-grafito">
        <tr>
          <th className="py-1.5 font-medium">Nombre</th>
          <th className="py-1.5 text-right font-medium">Margen</th>
          <th className="py-1.5 text-right font-medium">%</th>
          <th className="py-1.5 text-right font-medium">Aporte</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-niebla">
        {filas.map((r) => (
          <tr key={r.clave}>
            <td className="py-1.5 text-tinta">{r.nombre}</td>
            <td className="tabular py-1.5 text-right text-tinta">{formatCOP(r.margen)}</td>
            <td className="tabular py-1.5 text-right text-grafito">{formatPct(r.margen_bps)}</td>
            <td className="tabular py-1.5 text-right text-grafito">{formatPct(r.contribucion_bps)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
