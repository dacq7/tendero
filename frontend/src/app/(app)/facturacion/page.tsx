"use client";

import { type FormEvent, useEffect, useState } from "react";

import { ApiError, apiGet, apiPatch, apiPost } from "@/lib/api";
import type { InvoiceResolution } from "@/lib/types";

const vacio = {
  numero_resolucion: "",
  prefijo: "",
  numero_desde: "1",
  numero_hasta: "",
  vigencia_desde: "",
  vigencia_hasta: "",
  rut_nit: "",
  responsabilidad: "52",
};

export default function FacturacionPage() {
  const [resoluciones, setResoluciones] = useState<InvoiceResolution[]>([]);
  const [denegado, setDenegado] = useState(false);
  const [form, setForm] = useState({ ...vacio });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function cargar() {
    try {
      setResoluciones(await apiGet<InvoiceResolution[]>("fiscal/resolutions"));
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) setDenegado(true);
    }
  }

  useEffect(() => {
    let cancel = false;
    (async () => {
      try {
        const r = await apiGet<InvoiceResolution[]>("fiscal/resolutions");
        if (!cancel) setResoluciones(r);
      } catch (err) {
        if (err instanceof ApiError && err.status === 403 && !cancel) setDenegado(true);
      }
    })();
    return () => {
      cancel = true;
    };
  }, []);

  async function crear(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (Number(form.numero_desde) >= Number(form.numero_hasta)) {
      setError("El rango 'desde' debe ser menor que 'hasta'.");
      return;
    }
    setBusy(true);
    try {
      await apiPost("fiscal/resolutions", {
        numero_resolucion: form.numero_resolucion,
        prefijo: form.prefijo,
        numero_desde: Number(form.numero_desde),
        numero_hasta: Number(form.numero_hasta),
        vigencia_desde: form.vigencia_desde,
        vigencia_hasta: form.vigencia_hasta,
        rut_nit: form.rut_nit,
        responsabilidad: form.responsabilidad,
        activa: true, // crear activa: el backend desactiva la anterior
      });
      setForm({ ...vacio });
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear la resolución.");
    } finally {
      setBusy(false);
    }
  }

  async function activar(id: number) {
    setError(null);
    try {
      await apiPatch(`fiscal/resolutions/${id}`, { activa: true });
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo activar.");
    }
  }

  if (denegado) {
    return <p className="text-grafito">Esta sección es solo para administradores.</p>;
  }

  return (
    <div>
      <h1 className="font-display text-2xl font-bold text-tinta">Facturación · Resoluciones DIAN</h1>
      <p className="mt-1 text-sm text-grafito">
        Configura la resolución de numeración autorizada. Solo una puede estar activa. El número
        fiscal de cada factura se toma de su rango al emitir.
      </p>

      {error && (
        <div role="alert" className="mt-3 rounded-lg border border-achiote/30 bg-achiote/10 px-3 py-2 text-sm text-achiote">
          {error}
        </div>
      )}

      <div className="mt-4 grid gap-6 lg:grid-cols-[1.1fr_1fr]">
        <section className="overflow-hidden rounded-2xl border border-niebla bg-white">
          <table className="w-full text-sm">
            <thead className="border-b border-niebla bg-niebla/30 text-left text-grafito">
              <tr>
                <th className="px-4 py-2 font-medium">Resolución</th>
                <th className="px-4 py-2 font-medium">Rango</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-niebla">
              {resoluciones.length === 0 ? (
                <tr>
                  <td colSpan={3} className="px-4 py-6 text-center text-grafito">
                    Sin resoluciones.
                  </td>
                </tr>
              ) : (
                resoluciones.map((r) => (
                  <tr key={r.id} className={r.activa ? "bg-azulon/5" : undefined}>
                    <td className="px-4 py-2 text-tinta">
                      {r.prefijo} · {r.numero_resolucion}
                      {r.activa && <span className="ml-1 text-xs font-medium text-azulon">activa</span>}
                    </td>
                    <td className="tabular px-4 py-2 text-grafito">
                      {r.numero_desde}–{r.numero_hasta}
                      <span className="block text-[10px]">usados hasta {r.last_numero}</span>
                    </td>
                    <td className="px-4 py-2 text-right">
                      {!r.activa && (
                        <button onClick={() => activar(r.id)} className="text-sm text-azulon hover:underline">
                          Activar
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </section>

        <section className="rounded-2xl border border-niebla bg-white p-4">
          <h2 className="text-sm font-bold uppercase tracking-wide text-grafito">Nueva resolución</h2>
          <form onSubmit={crear} className="mt-3 space-y-3">
            <Campo label="Número de resolución (DIAN)">
              <input value={form.numero_resolucion} onChange={(e) => setForm({ ...form, numero_resolucion: e.target.value })} required className={inputCls} />
            </Campo>
            <div className="grid grid-cols-2 gap-3">
              <Campo label="Prefijo">
                <input value={form.prefijo} onChange={(e) => setForm({ ...form, prefijo: e.target.value })} required className={inputCls} />
              </Campo>
              <Campo label="RUT / NIT">
                <input value={form.rut_nit} onChange={(e) => setForm({ ...form, rut_nit: e.target.value })} required className={inputCls} />
              </Campo>
              <Campo label="Desde">
                <input type="number" min={1} value={form.numero_desde} onChange={(e) => setForm({ ...form, numero_desde: e.target.value })} required className={`${inputCls} tabular text-right`} />
              </Campo>
              <Campo label="Hasta">
                <input type="number" min={1} value={form.numero_hasta} onChange={(e) => setForm({ ...form, numero_hasta: e.target.value })} required className={`${inputCls} tabular text-right`} />
              </Campo>
              <Campo label="Vigencia desde">
                <input type="date" value={form.vigencia_desde} onChange={(e) => setForm({ ...form, vigencia_desde: e.target.value })} required className={inputCls} />
              </Campo>
              <Campo label="Vigencia hasta">
                <input type="date" value={form.vigencia_hasta} onChange={(e) => setForm({ ...form, vigencia_hasta: e.target.value })} required className={inputCls} />
              </Campo>
              <Campo label="Responsabilidad">
                <input value={form.responsabilidad} onChange={(e) => setForm({ ...form, responsabilidad: e.target.value })} className={inputCls} />
              </Campo>
            </div>
            <button type="submit" disabled={busy} className="h-11 w-full rounded-lg bg-achiote font-semibold text-papel transition hover:brightness-105 disabled:opacity-60">
              {busy ? "Creando…" : "Crear y activar"}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}

const inputCls =
  "mt-1 h-10 w-full rounded-lg border border-niebla bg-white px-3 text-tinta outline-none transition focus:border-azulon focus:ring-2 focus:ring-azulon/30";

function Campo({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block text-sm font-medium text-tinta">{label}{children}</label>;
}
