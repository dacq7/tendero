"use client";

import Link from "next/link";
import { type FormEvent, useEffect, useState } from "react";

import { ApiError, apiGet, apiPatch, apiPost } from "@/lib/api";
import type { Supplier } from "@/lib/types";

import AdminGuard from "../../AdminGuard";

const vacio = { nombre: "", nit: "", contacto_nombre: "", telefono: "", email: "", direccion: "" };

export default function ProveedoresPage() {
  const [proveedores, setProveedores] = useState<Supplier[]>([]);
  const [editId, setEditId] = useState<number | null>(null); // null = formulario de alta
  const [form, setForm] = useState({ ...vacio, activo: true });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function cargar() {
    const s = await apiGet<Supplier[]>("suppliers?solo_activos=false").catch(() => []);
    setProveedores(s);
  }

  useEffect(() => {
    let cancel = false;
    (async () => {
      const s = await apiGet<Supplier[]>("suppliers?solo_activos=false").catch(() => []);
      if (!cancel) setProveedores(s);
    })();
    return () => {
      cancel = true;
    };
  }, []);

  function nuevo() {
    setEditId(null);
    setForm({ ...vacio, activo: true });
    setError(null);
  }

  function editar(s: Supplier) {
    setEditId(s.id);
    setForm({
      nombre: s.nombre,
      nit: s.nit ?? "",
      contacto_nombre: s.contacto_nombre ?? "",
      telefono: s.telefono ?? "",
      email: s.email ?? "",
      direccion: s.direccion ?? "",
      activo: s.activo,
    });
    setError(null);
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    const body = {
      nombre: form.nombre,
      nit: form.nit || null,
      contacto_nombre: form.contacto_nombre || null,
      telefono: form.telefono || null,
      email: form.email || null,
      direccion: form.direccion || null,
    };
    try {
      if (editId) {
        await apiPatch(`suppliers/${editId}`, { ...body, activo: form.activo });
      } else {
        await apiPost("suppliers", body);
      }
      await cargar();
      nuevo();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar el proveedor.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AdminGuard>
      <Link href="/inventario" className="text-sm text-azulon hover:underline">
        ← Inventario
      </Link>
      <h1 className="mt-2 font-display text-2xl font-bold text-tinta">Proveedores</h1>

      <div className="mt-4 grid gap-6 lg:grid-cols-[1fr_1fr]">
        <section className="overflow-hidden rounded-2xl border border-niebla bg-white">
          <table className="w-full text-sm">
            <thead className="border-b border-niebla bg-niebla/30 text-left text-grafito">
              <tr>
                <th className="px-4 py-2 font-medium">Nombre</th>
                <th className="px-4 py-2 font-medium">NIT</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-niebla">
              {proveedores.length === 0 ? (
                <tr>
                  <td colSpan={3} className="px-4 py-6 text-center text-grafito">
                    Sin proveedores aún.
                  </td>
                </tr>
              ) : (
                proveedores.map((s) => (
                  <tr key={s.id} className={s.activo ? undefined : "opacity-50"}>
                    <td className="px-4 py-2 text-tinta">{s.nombre}</td>
                    <td className="px-4 py-2 text-grafito">{s.nit ?? "—"}</td>
                    <td className="px-4 py-2 text-right">
                      <button onClick={() => editar(s)} className="text-sm text-azulon hover:underline">
                        Editar
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </section>

        <section className="rounded-2xl border border-niebla bg-white p-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold uppercase tracking-wide text-grafito">
              {editId ? "Editar proveedor" : "Nuevo proveedor"}
            </h2>
            {editId && (
              <button onClick={nuevo} className="text-xs text-azulon hover:underline">
                + Nuevo
              </button>
            )}
          </div>
          <form onSubmit={submit} className="mt-3 space-y-3">
            {error && (
              <div role="alert" className="rounded-lg border border-achiote/30 bg-achiote/10 px-3 py-2 text-sm text-achiote">
                {error}
              </div>
            )}
            <Campo label="Nombre" requerido>
              <input value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} required className={inputCls} />
            </Campo>
            <div className="grid grid-cols-2 gap-3">
              <Campo label="NIT">
                <input value={form.nit} onChange={(e) => setForm({ ...form, nit: e.target.value })} className={inputCls} />
              </Campo>
              <Campo label="Teléfono">
                <input value={form.telefono} onChange={(e) => setForm({ ...form, telefono: e.target.value })} className={inputCls} />
              </Campo>
            </div>
            <Campo label="Contacto">
              <input value={form.contacto_nombre} onChange={(e) => setForm({ ...form, contacto_nombre: e.target.value })} className={inputCls} />
            </Campo>
            <Campo label="Email">
              <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className={inputCls} />
            </Campo>
            <Campo label="Dirección">
              <input value={form.direccion} onChange={(e) => setForm({ ...form, direccion: e.target.value })} className={inputCls} />
            </Campo>
            {editId && (
              <label className="flex items-center gap-2 text-sm text-tinta">
                <input type="checkbox" checked={form.activo} onChange={(e) => setForm({ ...form, activo: e.target.checked })} />
                Activo
              </label>
            )}
            <button type="submit" disabled={busy} className="h-11 w-full rounded-lg bg-achiote font-semibold text-papel transition hover:brightness-105 disabled:opacity-60">
              {busy ? "Guardando…" : editId ? "Guardar" : "Crear proveedor"}
            </button>
          </form>
        </section>
      </div>
    </AdminGuard>
  );
}

const inputCls =
  "mt-1 h-10 w-full rounded-lg border border-niebla bg-white px-3 text-tinta outline-none transition focus:border-azulon focus:ring-2 focus:ring-azulon/30";

function Campo({ label, requerido, children }: { label: string; requerido?: boolean; children: React.ReactNode }) {
  return (
    <label className="block text-sm font-medium text-tinta">
      {label}
      {requerido && <span className="text-achiote"> *</span>}
      {children}
    </label>
  );
}
