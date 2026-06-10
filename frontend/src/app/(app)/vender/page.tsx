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
import { formatCantidad, formatCOP } from "@/lib/money";
import { PAYMENT_METHODS, type PaymentMethod, type Product, type SaleRead } from "@/lib/types";

type Phase = "vender" | "cobrando" | "ticket";

const METODO_LABEL: Record<PaymentMethod, string> = {
  efectivo: "Efectivo",
  tarjeta: "Tarjeta",
  nequi: "Nequi",
  transferencia: "Transferencia",
};

export default function VenderPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Product[]>([]);
  const [cart, setCart] = useState<CartLine[]>([]);
  const [phase, setPhase] = useState<Phase>("vender");
  const [metodo, setMetodo] = useState<PaymentMethod>("efectivo");
  const [lastSale, setLastSale] = useState<SaleRead | null>(null);
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
      setLastSale(sale);
      setCart([]);
      setQuery("");
      setPhase("ticket");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cobrar. Intenta de nuevo.");
    } finally {
      setCobrando(false);
    }
  }

  function nuevaVenta() {
    setLastSale(null);
    setError(null);
    setPhase("vender");
  }

  if (phase === "ticket" && lastSale) {
    return <Ticket sale={lastSale} onNueva={nuevaVenta} />;
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
          <p className="tabular text-sm text-papel/70">{sale.invoice.numero_completo}</p>
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
