"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { formatCOP } from "@/lib/money";
import type { SupplierConcentration, SupplierMargin, SupplierPurchases } from "@/lib/types";

import {
  BotonCsv,
  Estado,
  Kpi,
  MARCA,
  Panel,
  type Rango,
  exportarCsv,
  formatPct,
  getRango,
  useFetch,
} from "./_ui";

const ejeY = (v: unknown) => formatCOP(Number(v) * 100);

export default function ProveedoresTab({ rango }: { rango: Rango }) {
  const f = useFetch(
    async () => {
      const [compras, margen, concentracion] = await Promise.all([
        getRango<SupplierPurchases[]>("analytics/suppliers/purchases", rango),
        getRango<SupplierMargin[]>("analytics/suppliers/margin", rango),
        getRango<SupplierConcentration>("analytics/suppliers/concentration", rango),
      ]);
      return { compras, margen, concentracion };
    },
    [rango.desde, rango.hasta],
  );

  return (
    <Estado fetch={f} vacio={f.data?.compras.length === 0 && f.data?.margen.length === 0}>
      {f.data && (
        <>
          <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-3">
            <Kpi label="Proveedores" valor={String(f.data.concentracion.n_proveedores)} />
            <Kpi
              label="Dependencia del principal"
              valor={formatPct(f.data.concentracion.concentracion_top1_bps)}
              sub="de las ventas vienen de 1 proveedor"
            />
            <Kpi
              label="Top 3 proveedores"
              valor={formatPct(f.data.concentracion.concentracion_top3_bps)}
              sub="concentración de las ventas"
            />
          </div>

          <Panel
            titulo="Compras por proveedor"
            acciones={<BotonCsv onClick={() => exportarCsv("suppliers", rango)} />}
          >
            {f.data.compras.length === 0 ? (
              <p className="text-sm text-grafito">Sin compras (entradas de inventario) en el periodo.</p>
            ) : (
              <ResponsiveContainer width="100%" height={Math.max(180, f.data.compras.length * 38)}>
                <BarChart
                  layout="vertical"
                  data={f.data.compras.map((s) => ({ nombre: s.nombre, compras: s.compras_centavos / 100 }))}
                  margin={{ top: 8, right: 16, left: 8, bottom: 4 }}
                >
                  <CartesianGrid stroke="#e4e1da" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 11, fill: "#5c5f66" }} tickFormatter={ejeY} />
                  <YAxis
                    type="category"
                    dataKey="nombre"
                    tick={{ fontSize: 11, fill: "#5c5f66" }}
                    width={140}
                  />
                  <Tooltip formatter={ejeY} />
                  <Bar dataKey="compras" fill={MARCA} radius={[0, 3, 3, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </Panel>

          <Panel titulo="Margen aportado por proveedor">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-grafito">
                <tr>
                  <th className="py-1.5 font-medium">Proveedor</th>
                  <th className="py-1.5 text-right font-medium">Ventas</th>
                  <th className="py-1.5 text-right font-medium">Margen</th>
                  <th className="py-1.5 text-right font-medium">%</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-niebla">
                {f.data.margen.map((s) => (
                  <tr key={s.supplier_id ?? "sin"}>
                    <td className="py-1.5 text-tinta">{s.nombre}</td>
                    <td className="tabular py-1.5 text-right text-tinta">{formatCOP(s.ventas_centavos)}</td>
                    <td className="tabular py-1.5 text-right text-tinta">{formatCOP(s.margen_centavos)}</td>
                    <td className="tabular py-1.5 text-right text-grafito">{formatPct(s.margen_bps)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>
        </>
      )}
    </Estado>
  );
}
