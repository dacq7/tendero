"use client";

import { formatCOP } from "@/lib/money";
import type { CustomerSegments, TopCustomer } from "@/lib/types";

import {
  BotonCsv,
  Estado,
  Kpi,
  Panel,
  type Rango,
  exportarCsv,
  getRango,
  useFetch,
} from "./_ui";

export default function ClientesTab({ rango }: { rango: Rango }) {
  const f = useFetch(
    async () => {
      const [top, segmentos] = await Promise.all([
        getRango<TopCustomer[]>("analytics/customers/top", rango, "&limit=10"),
        getRango<CustomerSegments>("analytics/customers/segments", rango),
      ]);
      return { top, segmentos };
    },
    [rango.desde, rango.hasta],
  );

  return (
    <Estado fetch={f}>
      {f.data && (
        <>
          <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Kpi
              label="Ticket cliente recurrente"
              valor={formatCOP(f.data.segmentos.identificado.ticket_promedio_centavos)}
              sub={`${f.data.segmentos.identificado.n_transacciones} compras`}
            />
            <Kpi
              label="Ticket consumidor final"
              valor={formatCOP(f.data.segmentos.anonimo.ticket_promedio_centavos)}
              sub={`${f.data.segmentos.anonimo.n_transacciones} compras anónimas`}
            />
            <Kpi
              label="Ventas a recurrentes"
              valor={formatCOP(f.data.segmentos.identificado.ventas_centavos)}
            />
            <Kpi
              label="Ventas anónimas"
              valor={formatCOP(f.data.segmentos.anonimo.ventas_centavos)}
            />
          </div>

          <Panel
            titulo="Mejores clientes"
            acciones={<BotonCsv onClick={() => exportarCsv("customers", rango)} />}
          >
            {f.data.top.length === 0 ? (
              <p className="text-sm text-grafito">
                Aún no hay clientes identificados. Registra el documento en la venta para verlos aquí.
              </p>
            ) : (
              <table className="w-full text-sm">
                <thead className="text-left text-xs uppercase tracking-wide text-grafito">
                  <tr>
                    <th className="py-1.5 font-medium">Cliente</th>
                    <th className="py-1.5 text-right font-medium">Compras</th>
                    <th className="py-1.5 text-right font-medium">Gasto total</th>
                    <th className="py-1.5 text-right font-medium">Ticket</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-niebla">
                  {f.data.top.map((c) => (
                    <tr key={c.customer_doc}>
                      <td className="py-1.5 text-tinta">
                        {c.nombre ?? "—"}
                        <span className="ml-1 text-xs text-grafito">· {c.customer_doc}</span>
                      </td>
                      <td className="tabular py-1.5 text-right text-grafito">{c.n_compras}</td>
                      <td className="tabular py-1.5 text-right text-tinta">{formatCOP(c.gasto_centavos)}</td>
                      <td className="tabular py-1.5 text-right text-grafito">
                        {formatCOP(c.ticket_promedio_centavos)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Panel>
        </>
      )}
    </Estado>
  );
}
