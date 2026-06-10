"use client";

import { formatCantidad, formatCOP } from "@/lib/money";
import type { LowStockRow, ReorderRow, RotacionResumen, StockoutRow } from "@/lib/types";

import {
  BotonCsv,
  Estado,
  Kpi,
  Panel,
  type Rango,
  exportarCsv,
  formatVeces,
  getRango,
  useFetch,
} from "./_ui";

export default function InventarioTab({ rango }: { rango: Rango }) {
  const f = useFetch(
    async () => {
      const [rotacion, low, reorder, stockouts] = await Promise.all([
        getRango<RotacionResumen>("analytics/inventory-rotation", rango),
        getRango<LowStockRow[]>("analytics/low-stock", { desde: rango.desde, hasta: rango.hasta }),
        getRango<ReorderRow[]>("analytics/reorder", rango),
        getRango<StockoutRow[]>("analytics/stockouts", rango),
      ]);
      return { rotacion, low, reorder, stockouts };
    },
    [rango.desde, rango.hasta],
  );

  const pctInmovilizado =
    f.data && f.data.rotacion.stock_valorizado_centavos > 0
      ? Math.round(
          (f.data.rotacion.capital_inmovilizado_centavos * 100) /
            f.data.rotacion.stock_valorizado_centavos,
        )
      : 0;

  return (
    <Estado fetch={f}>
      {f.data && (
        <>
          <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Kpi label="Stock valorizado" valor={formatCOP(f.data.rotacion.stock_valorizado_centavos)} />
            <Kpi
              label="Rotación"
              valor={`${formatVeces(f.data.rotacion.rotacion_centi)}/año`}
              sub={f.data.rotacion.dias_inventario !== null ? `${f.data.rotacion.dias_inventario} días de inventario` : undefined}
            />
            <Kpi
              label="Capital inmovilizado"
              valor={formatCOP(f.data.rotacion.capital_inmovilizado_centavos)}
              sub={`${pctInmovilizado}% del stock · rota lento (>180 días)`}
            />
            <Kpi label="Bajo el mínimo" valor={String(f.data.low.length)} />
          </div>

          <Panel
            titulo="Rotación por producto"
            acciones={<BotonCsv onClick={() => exportarCsv("inventory-rotation", rango)} />}
          >
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-grafito">
                <tr>
                  <th className="py-1.5 font-medium">Producto</th>
                  <th className="py-1.5 text-right font-medium">Stock valorizado</th>
                  <th className="py-1.5 text-right font-medium">Rotación</th>
                  <th className="py-1.5 text-right font-medium">Días</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-niebla">
                {f.data.rotacion.por_producto.map((p) => {
                  const lento = p.dias_inventario !== null && p.dias_inventario > 180;
                  return (
                    <tr key={p.product_id}>
                      <td className="py-1.5 text-tinta">{p.nombre}</td>
                      <td className="tabular py-1.5 text-right text-tinta">
                        {formatCOP(p.stock_valorizado_centavos)}
                      </td>
                      <td className="tabular py-1.5 text-right text-grafito">
                        {formatVeces(p.rotacion_centi)}
                      </td>
                      <td className={`tabular py-1.5 text-right ${lento ? "text-achiote" : "text-grafito"}`}>
                        {p.dias_inventario ?? "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Panel>

          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <Panel titulo="Sugerencias de recompra">
              {f.data.reorder.length === 0 ? (
                <p className="text-sm text-grafito">Nada urgente: ningún producto que rote está bajo el mínimo.</p>
              ) : (
                <table className="w-full text-sm">
                  <thead className="text-left text-xs uppercase tracking-wide text-grafito">
                    <tr>
                      <th className="py-1.5 font-medium">Producto</th>
                      <th className="py-1.5 text-right font-medium">Stock</th>
                      <th className="py-1.5 text-right font-medium">Pedir</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-niebla">
                    {f.data.reorder.map((r) => (
                      <tr key={r.product_id}>
                        <td className="py-1.5 text-tinta">{r.nombre}</td>
                        <td className="tabular py-1.5 text-right text-grafito">
                          {formatCantidad(r.stock_milesimas)}
                        </td>
                        <td className="tabular py-1.5 text-right font-semibold text-achiote">
                          {formatCantidad(r.cantidad_sugerida_milesimas)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Panel>

            <Panel titulo="Quiebres de stock (tocaron cero)">
              {f.data.stockouts.length === 0 ? (
                <p className="text-sm text-grafito">Ningún producto llegó a cero en el periodo.</p>
              ) : (
                <table className="w-full text-sm">
                  <thead className="text-left text-xs uppercase tracking-wide text-grafito">
                    <tr>
                      <th className="py-1.5 font-medium">Producto</th>
                      <th className="py-1.5 text-right font-medium">Veces en cero</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-niebla">
                    {f.data.stockouts.map((s) => (
                      <tr key={s.product_id}>
                        <td className="py-1.5 text-tinta">{s.nombre}</td>
                        <td className="tabular py-1.5 text-right text-grafito">{s.veces_en_cero}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Panel>
          </div>
        </>
      )}
    </Estado>
  );
}
