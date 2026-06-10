"use client";

import { type FormEvent, useState } from "react";

import { ApiError, apiPatch, apiPost } from "@/lib/api";
import { centavosAPesos, milesimasAUnidades, pesosACentavos, unidadesAMilesimas } from "@/lib/forms";
import { formatCantidad } from "@/lib/money";
import type { Product, Supplier } from "@/lib/types";

const IVA_OPCIONES = [
  { value: "exento", label: "Exento" },
  { value: "tarifa_0", label: "0%" },
  { value: "tarifa_5", label: "5%" },
  { value: "tarifa_19", label: "19%" },
];
const UNIDAD_OPCIONES = ["unidad", "kg", "g", "litro", "ml", "paquete"];

export default function ProductoForm({
  producto,
  proveedores,
  onDone,
}: {
  producto?: Product;
  proveedores: Supplier[];
  onDone: () => void;
}) {
  const esEdicion = Boolean(producto);
  const [nombre, setNombre] = useState(producto?.nombre ?? "");
  const [sku, setSku] = useState(producto?.sku ?? "");
  const [codigoBarras, setCodigoBarras] = useState(producto?.codigo_barras ?? "");
  const [categoria, setCategoria] = useState(producto?.categoria ?? "");
  const [supplierId, setSupplierId] = useState(producto?.supplier_id ? String(producto.supplier_id) : "");
  const [costo, setCosto] = useState(producto ? String(centavosAPesos(producto.precio_costo_centavos)) : "");
  const [venta, setVenta] = useState(producto ? String(centavosAPesos(producto.precio_venta_centavos)) : "");
  const [iva, setIva] = useState(producto?.iva ?? "tarifa_19");
  const [unidad, setUnidad] = useState(producto?.unidad ?? "unidad");
  const [stockMinimo, setStockMinimo] = useState(
    producto ? String(milesimasAUnidades(producto.stock_minimo_milesimas)) : "0",
  );
  const [activo, setActivo] = useState(producto?.activo ?? true);
  // Solo en alta: entrada inicial opcional (no es un campo de stock libre).
  const [stockInicial, setStockInicial] = useState("");
  const [costoInicial, setCostoInicial] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const base = {
        nombre,
        sku,
        codigo_barras: codigoBarras || null,
        categoria: categoria || null,
        supplier_id: supplierId ? Number(supplierId) : null,
        precio_costo_centavos: pesosACentavos(costo),
        precio_venta_centavos: pesosACentavos(venta),
        iva,
        unidad,
        stock_minimo_milesimas: unidadesAMilesimas(stockMinimo),
        // NOTA: stock_milesimas NO se envía nunca — el stock cambia por movimientos.
      };
      if (esEdicion && producto) {
        await apiPatch(`products/${producto.id}`, { ...base, activo });
      } else {
        const creado = await apiPost<Product>("products", base);
        const cant = unidadesAMilesimas(stockInicial);
        if (cant > 0) {
          await apiPost("inventory/movements", {
            product_id: creado.id,
            tipo: "entrada",
            cantidad_milesimas: cant,
            costo_unitario_centavos: pesosACentavos(costoInicial),
            motivo: "Carga inicial",
          });
        }
      }
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar el producto.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="max-w-xl space-y-4">
      {error && (
        <div role="alert" className="rounded-lg border border-achiote/30 bg-achiote/10 px-3 py-2 text-sm text-achiote">
          {error}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <Campo label="Nombre" requerido>
          <input value={nombre} onChange={(e) => setNombre(e.target.value)} required className={inputCls} />
        </Campo>
        <Campo label="SKU" requerido>
          <input value={sku} onChange={(e) => setSku(e.target.value)} required className={inputCls} />
        </Campo>
        <Campo label="Código de barras">
          <input value={codigoBarras} onChange={(e) => setCodigoBarras(e.target.value)} className={inputCls} />
        </Campo>
        <Campo label="Categoría">
          <input value={categoria} onChange={(e) => setCategoria(e.target.value)} className={inputCls} />
        </Campo>
        <Campo label="Proveedor">
          <select value={supplierId} onChange={(e) => setSupplierId(e.target.value)} className={inputCls}>
            <option value="">— Sin proveedor —</option>
            {proveedores.map((s) => (
              <option key={s.id} value={s.id}>
                {s.nombre}
              </option>
            ))}
          </select>
        </Campo>
        <Campo label="IVA">
          <select value={iva} onChange={(e) => setIva(e.target.value as Product["iva"])} className={inputCls}>
            {IVA_OPCIONES.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </Campo>
        <Campo label="Precio costo (pesos)">
          <input type="number" min={0} step={1} value={costo} onChange={(e) => setCosto(e.target.value)} className={`${inputCls} tabular text-right`} />
        </Campo>
        <Campo label="Precio venta (pesos)">
          <input type="number" min={0} step={1} value={venta} onChange={(e) => setVenta(e.target.value)} className={`${inputCls} tabular text-right`} />
        </Campo>
        <Campo label="Unidad">
          <select value={unidad} onChange={(e) => setUnidad(e.target.value)} className={inputCls}>
            {UNIDAD_OPCIONES.map((u) => (
              <option key={u} value={u}>
                {u}
              </option>
            ))}
          </select>
        </Campo>
        <Campo label="Stock mínimo (unidades)">
          <input type="number" min={0} step={1} value={stockMinimo} onChange={(e) => setStockMinimo(e.target.value)} className={`${inputCls} tabular text-right`} />
        </Campo>
      </div>

      {esEdicion && producto && (
        <div className="rounded-lg border border-niebla bg-niebla/20 p-3">
          <p className="text-sm font-medium text-tinta">
            Stock actual:{" "}
            <span className="tabular" data-testid="stock-readonly">
              {formatCantidad(producto.stock_milesimas)}
            </span>
          </p>
          <p className="mt-1 text-xs text-grafito">
            El stock no se edita aquí: cambia con entradas, mermas y ajustes de inventario.
          </p>
          <label className="mt-3 flex items-center gap-2 text-sm text-tinta">
            <input type="checkbox" checked={activo} onChange={(e) => setActivo(e.target.checked)} />
            Producto activo
          </label>
        </div>
      )}

      {!esEdicion && (
        <div className="rounded-lg border border-niebla bg-niebla/20 p-3">
          <p className="text-sm font-medium text-tinta">Entrada inicial (opcional)</p>
          <p className="mt-1 text-xs text-grafito">
            El stock no es un campo: si cargas existencia inicial, se registra como una
            entrada de inventario (con su costo, recalcula el CMP).
          </p>
          <div className="mt-2 grid gap-3 sm:grid-cols-2">
            <Campo label="Cantidad inicial (unidades)">
              <input type="number" min={0} step={1} value={stockInicial} onChange={(e) => setStockInicial(e.target.value)} className={`${inputCls} tabular text-right`} />
            </Campo>
            <Campo label="Costo unitario (pesos)">
              <input type="number" min={0} step={1} value={costoInicial} onChange={(e) => setCostoInicial(e.target.value)} className={`${inputCls} tabular text-right`} />
            </Campo>
          </div>
        </div>
      )}

      <div className="flex gap-2">
        <button type="button" onClick={onDone} className="h-11 flex-1 rounded-lg border border-niebla font-medium text-tinta transition hover:bg-niebla/60">
          Cancelar
        </button>
        <button type="submit" disabled={busy} className="h-11 flex-1 rounded-lg bg-achiote font-semibold text-papel transition hover:brightness-105 disabled:opacity-60">
          {busy ? "Guardando…" : esEdicion ? "Guardar cambios" : "Crear producto"}
        </button>
      </div>
    </form>
  );
}

const inputCls =
  "mt-1 h-11 w-full rounded-lg border border-niebla bg-white px-3 text-tinta outline-none transition focus:border-azulon focus:ring-2 focus:ring-azulon/30";

function Campo({
  label,
  requerido,
  children,
}: {
  label: string;
  requerido?: boolean;
  children: React.ReactNode;
}) {
  return (
    <label className="block text-sm font-medium text-tinta">
      {label}
      {requerido && <span className="text-achiote"> *</span>}
      {children}
    </label>
  );
}
