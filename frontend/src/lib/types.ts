// Tipos de las respuestas del backend usados por las pantallas.

import type { IvaRate } from "./money";

export interface UserMe {
  id: number;
  email: string;
  full_name: string;
  role: "admin" | "cajero";
}

export interface Product {
  id: number;
  nombre: string;
  sku: string;
  codigo_barras: string | null;
  categoria: string | null;
  precio_venta_centavos: number;
  precio_costo_centavos: number;
  iva: IvaRate;
  unidad: string;
  stock_milesimas: number;
  stock_minimo_milesimas: number;
  margen_centavos: number;
  margen_bps: number | null;
  stock_bajo: boolean;
  activo: boolean;
}

export type DianStatus = "none" | "pending" | "accepted" | "rejected";

export interface InvoiceRead {
  id: number;
  sale_id: number;
  numero_completo: string;
  subtotal_centavos: number;
  iva_total_centavos: number;
  total_centavos: number;
  metodo_pago: string;
  dian_status: DianStatus;
  cufe: string | null;
  created_at: string;
}

export interface FiscalEmissionRead {
  id: number;
  invoice_id: number;
  numero_fiscal_completo: string;
  provider: string;
  status: DianStatus;
  cufe: string | null;
  motivo_rechazo: string | null;
  intentos: number;
}

export interface SaleItemRead {
  id: number;
  nombre_snapshot: string;
  sku_snapshot: string;
  cantidad_milesimas: number;
  precio_unitario_centavos: number;
  base_centavos: number;
  iva_centavos: number;
  total_linea_centavos: number;
}

export interface SaleRead {
  id: number;
  subtotal_centavos: number;
  iva_total_centavos: number;
  total_centavos: number;
  status: string;
  metodo_pago: string | null;
  paid_at: string | null;
  created_at: string;
  items: SaleItemRead[];
  // null mientras el pago Wompi no se confirma (pendiente_pago / rechazada).
  invoice: InvoiceRead | null;
}

export type PaymentStatus = "pending" | "approved" | "declined" | "error" | "voided";

export interface PaymentRead {
  id: number;
  sale_id: number;
  provider: string;
  metodo: string;
  status: PaymentStatus;
  monto_centavos: number;
  referencia: string;
  wompi_transaction_id: string | null;
  wompi_public_key: string | null;
}

export interface CashSession {
  id: number;
  user_id: number;
  status: "abierta" | "cerrada";
  monto_inicial_centavos: number;
  abierta_at: string;
  cerrada_at: string | null;
  efectivo_contado_centavos: number | null;
  efectivo_esperado_centavos: number | null;
  diferencia_centavos: number | null;
}

// ── Analítica ──
export type Granularidad = "dia" | "semana" | "mes" | "ano";

export interface SummaryComparison {
  ventas_centavos: number;
  n_transacciones: number;
  ticket_promedio_centavos: number;
  margen_centavos: number;
  delta_ventas_bps: number | null;
  delta_transacciones_bps: number | null;
  delta_ticket_bps: number | null;
  delta_margen_bps: number | null;
}

export interface AnalyticsSummary {
  desde: string;
  hasta: string;
  ventas_centavos: number;
  subtotal_centavos: number;
  iva_centavos: number;
  cogs_centavos: number;
  n_transacciones: number;
  ticket_promedio_centavos: number;
  margen_centavos: number;
  margen_bps: number | null;
  comparativa: SummaryComparison | null;
}

export interface TimeSeriesPoint {
  periodo: string;
  ventas_centavos: number;
  n_transacciones: number;
  margen_centavos: number;
}

export interface TopProduct {
  product_id: number;
  nombre: string;
  ventas_centavos: number;
  cantidad_milesimas: number;
  margen_centavos: number;
}

export interface ByMethodRow {
  metodo: string;
  ventas_centavos: number;
  n_transacciones: number;
}

export interface InventoryStats {
  stock_valorizado_centavos: number;
  cogs_periodo_centavos: number;
  rotacion_bps: number | null;
  n_stock_bajo: number;
}

export const PAYMENT_METHODS = [
  "efectivo",
  "transferencia",
  "tarjeta",
  "pse",
  "nequi",
] as const;
export type PaymentMethod = (typeof PAYMENT_METHODS)[number];

// Métodos que se cobran por Wompi (asíncrono); el resto es cobro local.
export const WOMPI_METHODS: ReadonlySet<string> = new Set(["tarjeta", "pse", "nequi"]);
