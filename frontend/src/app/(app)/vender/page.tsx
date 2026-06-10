"use client";

import { useEffect, useMemo, useState } from "react";

import { ApiError, apiGet, apiPost } from "@/lib/api";
import {
  addToCart,
  type CartLine,
  cartTotals,
  lineTotals,
  removeFromCart,
  setCantidad,
  toSalePayload,
} from "@/lib/cart";
import { type CobroPhase, isWompiMethod } from "@/lib/cobro";
import { formatCantidad, formatCOP } from "@/lib/money";
import {
  PAYMENT_METHODS,
  type PaymentMethod,
  type PaymentRead,
  type Product,
  type SaleRead,
} from "@/lib/types";

const METODO_LABEL: Record<PaymentMethod, string> = {
  efectivo: "Efectivo",
  transferencia: "Transferencia",
  tarjeta: "Tarjeta",
  pse: "PSE",
  nequi: "Nequi",
};

export default function VenderPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Product[]>([]);
  const [cart, setCart] = useState<CartLine[]>([]);
  const [phase, setPhase] = useState<CobroPhase>("vender");
  const [metodo, setMetodo] = useState<PaymentMethod>("efectivo");
  const [lastSale, setLastSale] = useState<SaleRead | null>(null);
  const [payment, setPayment] = useState<PaymentRead | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cobrando, setCobrando] = useState(false);

  const totals = useMemo(() => cartTotals(cart), [cart]);

  const term = query.trim();

  useEffect(() => {
    if (term.length < 1) return;
    let cancel = false;
    apiGet<Product[]>(`products?q=${encodeURIComponent(term)}&limit=12`)
      .then((data) => {
        if (!cancel) setResults(data);
      })
      .catch(() => {
        if (!cancel) setResults([]);
      });
    return () => {
      cancel = true;
    };
  }, [term]);

  // Solo mostramos resultados mientras hay término de búsqueda.
  const visibles = term.length >= 1 ? results : [];

  function add(product: Product) {
    setCart((c) => addToCart(c, product));
  }

  async function confirmarCobro() {
    setError(null);
    setCobrando(true);
    try {
      const sale = await apiPost<SaleRead>("sales", toSalePayload(cart, metodo));
      setCart([]);
      setQuery("");
      if (!isWompiMethod(metodo)) {
        // Cobro local (efectivo/transferencia): la venta ya viene pagada.
        setLastSale(sale);
        setPhase("ticket");
        return;
      }
      // Cobro Wompi: iniciar el pago; la confirmación llega async (webhook).
      const pago = await apiPost<PaymentRead>("payments", { sale_id: sale.id });
      setLastSale(sale);
      setPayment(pago);
      setPhase("procesando");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cobrar. Intenta de nuevo.");
    } finally {
      setCobrando(false);
    }
  }

  // Cierra el pago Wompi: carga la venta con su factura (approved) o muestra rechazo.
  async function resolverPago(aprobado: boolean) {
    if (!lastSale) return;
    if (!aprobado) {
      setPhase("rechazado");
      return;
    }
    const sale = await apiGet<SaleRead>(`sales/${lastSale.id}`);
    setLastSale(sale);
    setPhase("ticket");
  }

  function nuevaVenta() {
    setLastSale(null);
    setPayment(null);
    setError(null);
    setPhase("vender");
  }

  if (phase === "ticket" && lastSale) {
    return <Ticket sale={lastSale} onNueva={nuevaVenta} />;
  }

  if (phase === "procesando" && payment) {
    return <Procesando payment={payment} onResolved={resolverPago} onCancel={nuevaVenta} />;
  }

  if (phase === "rechazado") {
    return <Rechazado onNueva={nuevaVenta} />;
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
      {/* Buscador + resultados */}
      <section>
        <label htmlFor="buscar" className="block text-sm font-medium text-grafito">
          Buscar producto
        </label>
        <input
          id="buscar"
          autoFocus
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Nombre, SKU o código de barras"
          className="mt-1.5 h-14 w-full rounded-xl border border-niebla bg-white px-4 text-lg text-tinta outline-none transition focus:border-azulon focus:ring-2 focus:ring-azulon/30"
        />
        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          {visibles.map((p) => (
            <button
              key={p.id}
              onClick={() => add(p)}
              className="flex flex-col items-start rounded-xl border border-niebla bg-white p-3 text-left transition hover:border-azulon hover:bg-azulon/5 focus-visible:ring-2 focus-visible:ring-azulon/40"
            >
              <span className="font-medium text-tinta">{p.nombre}</span>
              <span className="text-xs text-grafito">{p.sku}</span>
              <span className="tabular mt-1 text-sm text-azulon">
                {formatCOP(p.precio_venta_centavos)}
              </span>
            </button>
          ))}
          {term.length >= 1 && visibles.length === 0 && (
            <p className="text-sm text-grafito">No encontramos productos para “{query}”.</p>
          )}
        </div>
      </section>

      {/* Carrito */}
      <section className="flex flex-col rounded-2xl border border-niebla bg-white p-4">
        <h2 className="font-display text-lg font-bold text-tinta">Carrito</h2>
        {cart.length === 0 ? (
          <p className="mt-6 text-sm text-grafito">
            Busca un producto y tócalo para agregarlo a la venta.
          </p>
        ) : (
          <ul className="mt-3 flex-1 divide-y divide-niebla">
            {cart.map((line) => {
              const lt = lineTotals(line);
              return (
                <li key={line.product.id} className="flex items-center gap-2 py-2">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-tinta">{line.product.nombre}</p>
                    <p className="tabular text-xs text-grafito">
                      {formatCOP(line.product.precio_venta_centavos)} c/u
                    </p>
                  </div>
                  <input
                    aria-label={`Cantidad de ${line.product.nombre}`}
                    type="number"
                    min={0}
                    step={0.001}
                    value={line.cantidad_milesimas / 1000}
                    onChange={(e) =>
                      setCart((c) =>
                        setCantidad(c, line.product.id, Math.round(Number(e.target.value) * 1000)),
                      )
                    }
                    className="tabular h-9 w-16 rounded-md border border-niebla px-2 text-right text-sm"
                  />
                  <span className="tabular w-20 text-right text-sm text-tinta">
                    {formatCOP(lt.total_linea_centavos)}
                  </span>
                  <button
                    aria-label={`Quitar ${line.product.nombre}`}
                    onClick={() => setCart((c) => removeFromCart(c, line.product.id))}
                    className="text-grafito transition hover:text-achiote"
                  >
                    ✕
                  </button>
                </li>
              );
            })}
          </ul>
        )}

        <dl className="mt-4 space-y-1 border-t border-niebla pt-3 text-sm">
          <Row label="Subtotal" value={totals.subtotal_centavos} />
          <Row label="IVA" value={totals.iva_total_centavos} />
          <div className="flex justify-between pt-1 text-base font-bold text-tinta">
            <dt>Total</dt>
            <dd className="tabular" data-testid="cart-total">
              {formatCOP(totals.total_centavos)}
            </dd>
          </div>
        </dl>

        <button
          disabled={cart.length === 0}
          onClick={() => {
            setError(null);
            setPhase("cobrando");
          }}
          className="mt-4 h-12 rounded-xl bg-achiote font-semibold text-papel transition hover:brightness-105 focus-visible:ring-2 focus-visible:ring-achiote/40 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Cobrar
        </button>
      </section>

      {phase === "cobrando" && (
        <CobroModal
          total={totals.total_centavos}
          metodo={metodo}
          setMetodo={setMetodo}
          onCancel={() => setPhase("vender")}
          onConfirm={confirmarCobro}
          loading={cobrando}
          error={error}
        />
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex justify-between text-grafito">
      <dt>{label}</dt>
      <dd className="tabular">{formatCOP(value)}</dd>
    </div>
  );
}

function CobroModal({
  total,
  metodo,
  setMetodo,
  onCancel,
  onConfirm,
  loading,
  error,
}: {
  total: number;
  metodo: PaymentMethod;
  setMetodo: (m: PaymentMethod) => void;
  onCancel: () => void;
  onConfirm: () => void;
  loading: boolean;
  error: string | null;
}) {
  return (
    <div className="fixed inset-0 z-20 flex items-center justify-center bg-tinta/40 p-4">
      <div role="dialog" aria-label="Cobro" className="w-full max-w-sm rounded-2xl bg-papel p-6">
        <p className="text-sm text-grafito">Total a cobrar</p>
        <p className="tabular font-display text-4xl font-extrabold text-tinta">
          {formatCOP(total)}
        </p>
        <p className="mt-4 text-sm font-medium text-tinta">Método de pago</p>
        <div className="mt-2 grid grid-cols-2 gap-2">
          {PAYMENT_METHODS.map((m) => (
            <button
              key={m}
              onClick={() => setMetodo(m)}
              aria-pressed={metodo === m}
              className={`h-11 rounded-lg border text-sm font-medium transition ${
                metodo === m
                  ? "border-azulon bg-azulon/10 text-azulon"
                  : "border-niebla text-grafito hover:bg-niebla/60"
              }`}
            >
              {METODO_LABEL[m]}
            </button>
          ))}
        </div>
        {error && (
          <div role="alert" className="mt-4 rounded-lg border border-achiote/30 bg-achiote/10 px-3 py-2 text-sm text-achiote">
            {error}
          </div>
        )}
        <div className="mt-6 flex gap-2">
          <button
            onClick={onCancel}
            className="h-11 flex-1 rounded-lg border border-niebla font-medium text-tinta transition hover:bg-niebla/60"
          >
            Cancelar
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="h-11 flex-1 rounded-lg bg-achiote font-semibold text-papel transition hover:brightness-105 disabled:opacity-60"
          >
            {loading ? "Cobrando…" : "Confirmar"}
          </button>
        </div>
      </div>
    </div>
  );
}

function Ticket({ sale, onNueva }: { sale: SaleRead; onNueva: () => void }) {
  return (
    <div className="mx-auto max-w-sm">
      {/* El elemento audaz: el ticket de cobro (sección 14 del brief). */}
      <div className="overflow-hidden rounded-2xl border-2 border-tinta bg-papel shadow-[6px_6px_0_0_var(--color-achiote)]">
        <div className="bg-tinta px-5 py-4 text-papel">
          <p className="font-display text-xl font-extrabold">Tendero</p>
          <p className="tabular text-sm text-papel/70">{sale.invoice?.numero_completo}</p>
        </div>
        <div className="px-5 py-4">
          <ul className="divide-y divide-niebla">
            {sale.items.map((it) => (
              <li key={it.id} className="flex justify-between gap-2 py-1.5 text-sm">
                <span className="text-tinta">
                  {it.nombre_snapshot}
                  <span className="tabular text-grafito"> ×{formatCantidad(it.cantidad_milesimas)}</span>
                </span>
                <span className="tabular text-tinta">{formatCOP(it.total_linea_centavos)}</span>
              </li>
            ))}
          </ul>
          <dl className="mt-3 space-y-1 border-t border-niebla pt-3 text-sm">
            <Row label="Subtotal" value={sale.subtotal_centavos} />
            <Row label="IVA" value={sale.iva_total_centavos} />
            <div className="flex justify-between pt-1 text-lg font-bold text-achiote">
              <dt>Total</dt>
              <dd className="tabular">{formatCOP(sale.total_centavos)}</dd>
            </div>
          </dl>
          <p className="mt-3 text-xs capitalize text-grafito">Pago: {sale.metodo_pago}</p>
        </div>
      </div>
      <button
        onClick={onNueva}
        className="mt-4 h-12 w-full rounded-xl bg-azulon font-semibold text-papel transition hover:brightness-110"
      >
        Nueva venta
      </button>
    </div>
  );
}

function Procesando({
  payment,
  onResolved,
  onCancel,
}: {
  payment: PaymentRead;
  onResolved: (aprobado: boolean) => void;
  onCancel: () => void;
}) {
  const esMock = payment.provider === "mock";
  const [simulando, setSimulando] = useState(false);

  // En modo real (Wompi de verdad) la confirmación llega async: hacemos polling.
  // En modo mock el ciclo se cierra con los botones de simulación de abajo.
  useEffect(() => {
    if (esMock) return;
    let cancel = false;
    const id = setInterval(async () => {
      try {
        const p = await apiGet<PaymentRead>(`payments/${payment.id}`);
        if (cancel) return;
        if (p.status === "approved") onResolved(true);
        else if (p.status !== "pending") onResolved(false);
      } catch {
        /* reintenta en el siguiente tick */
      }
    }, 2500);
    return () => {
      cancel = true;
      clearInterval(id);
    };
  }, [esMock, payment.id, onResolved]);

  async function simular(result: "approved" | "declined") {
    setSimulando(true);
    try {
      await apiPost(`payments/${payment.id}/simulate`, { result });
      onResolved(result === "approved");
    } finally {
      setSimulando(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm text-center">
      <div className="rounded-2xl border border-niebla bg-white p-6">
        <div
          className="mx-auto h-10 w-10 rounded-full border-3 border-niebla border-t-azulon motion-safe:animate-spin"
          role="status"
          aria-label="Procesando pago"
        />
        <p className="mt-4 font-display text-lg font-bold text-tinta">Procesando pago</p>
        <p className="tabular mt-1 text-2xl font-extrabold text-tinta">
          {formatCOP(payment.monto_centavos)}
        </p>
        <p className="mt-1 text-sm capitalize text-grafito">{payment.metodo}</p>

        {esMock && (
          <div className="mt-6 rounded-xl border border-dashed border-azulon/40 bg-azulon/5 p-3">
            <p className="text-xs font-medium text-azulon">Modo demo — simular resultado</p>
            <div className="mt-2 flex gap-2">
              <button
                onClick={() => simular("approved")}
                disabled={simulando}
                className="h-10 flex-1 rounded-lg bg-azulon text-sm font-semibold text-papel transition hover:brightness-110 disabled:opacity-60"
              >
                Aprobar
              </button>
              <button
                onClick={() => simular("declined")}
                disabled={simulando}
                className="h-10 flex-1 rounded-lg border border-achiote/40 text-sm font-semibold text-achiote transition hover:bg-achiote/10 disabled:opacity-60"
              >
                Rechazar
              </button>
            </div>
          </div>
        )}
      </div>
      <button onClick={onCancel} className="mt-4 text-sm text-grafito underline">
        Cancelar
      </button>
    </div>
  );
}

function Rechazado({ onNueva }: { onNueva: () => void }) {
  return (
    <div className="mx-auto max-w-sm text-center">
      <div className="rounded-2xl border-2 border-achiote/40 bg-achiote/5 p-6">
        <p className="font-display text-xl font-bold text-achiote">Pago rechazado</p>
        <p className="mt-2 text-sm text-grafito">
          El pago no se completó. El stock se devolvió al inventario. Intenta con otro
          método o vuelve a cobrar.
        </p>
      </div>
      <button
        onClick={onNueva}
        className="mt-4 h-12 w-full rounded-xl bg-azulon font-semibold text-papel transition hover:brightness-110"
      >
        Nueva venta
      </button>
    </div>
  );
}
