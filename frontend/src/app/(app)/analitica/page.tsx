"use client";

import { useMemo, useState } from "react";

import { type Preset, rangoDePreset } from "@/lib/rango";
import type { Granularidad } from "@/lib/types";

import AdminGuard from "../AdminGuard";
import ClientesTab from "./ClientesTab";
import InventarioTab from "./InventarioTab";
import ProveedoresTab from "./ProveedoresTab";
import RentabilidadTab from "./RentabilidadTab";
import ResumenTab from "./ResumenTab";
import TendenciasTab from "./TendenciasTab";
import type { Rango } from "./_ui";

const PRESETS: { key: Preset; label: string; gran: Granularidad }[] = [
  { key: "7d", label: "7 días", gran: "dia" },
  { key: "30d", label: "30 días", gran: "dia" },
  { key: "mes", label: "Este mes", gran: "dia" },
  { key: "ano", label: "Este año", gran: "mes" },
];

type TabKey = "resumen" | "rentabilidad" | "inventario" | "proveedores" | "clientes" | "tendencias";

const TABS: { key: TabKey; label: string }[] = [
  { key: "resumen", label: "Resumen" },
  { key: "rentabilidad", label: "Rentabilidad" },
  { key: "inventario", label: "Inventario" },
  { key: "proveedores", label: "Proveedores" },
  { key: "clientes", label: "Clientes" },
  { key: "tendencias", label: "Tendencias" },
];

export default function AnaliticaPage() {
  const [preset, setPreset] = useState<Preset>("30d");
  const [gran, setGran] = useState<Granularidad>("dia");
  const [tab, setTab] = useState<TabKey>("resumen");

  // Hoy fijo por render del cambio de preset (evita recomputar el rango en cada render).
  const rango: Rango = useMemo(() => rangoDePreset(preset, new Date()), [preset]);

  return (
    <AdminGuard>
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
                preset === pr.key ? "bg-azulon/10 text-azulon" : "text-grafito hover:bg-niebla/60"
              }`}
            >
              {pr.label}
            </button>
          ))}
        </div>
      </div>

      <nav className="mt-4 flex gap-1 overflow-x-auto border-b border-niebla" aria-label="Secciones">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            aria-current={tab === t.key ? "page" : undefined}
            className={`whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium transition ${
              tab === t.key
                ? "border-azulon text-azulon"
                : "border-transparent text-grafito hover:text-tinta"
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {/* Solo la pestaña activa se monta → fetch lazy por sección. */}
      {tab === "resumen" && <ResumenTab rango={rango} gran={gran} />}
      {tab === "rentabilidad" && <RentabilidadTab rango={rango} />}
      {tab === "inventario" && <InventarioTab rango={rango} />}
      {tab === "proveedores" && <ProveedoresTab rango={rango} />}
      {tab === "clientes" && <ClientesTab rango={rango} />}
      {tab === "tendencias" && <TendenciasTab rango={rango} />}
    </AdminGuard>
  );
}
