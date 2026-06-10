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

export interface InvoiceRead {
  id: number;
  sale_id: number;
  numero_completo: string;
  subtotal_centavos: number;
  iva_total_centavos: number;
  total_centavos: number;
  metodo_pago: string;
  dian_status: string;
  created_at: string;
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
  created_at: string;
  items: SaleItemRead[];
  invoice: InvoiceRead;
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

export const PAYMENT_METHODS = ["efectivo", "tarjeta", "nequi", "transferencia"] as const;
export type PaymentMethod = (typeof PAYMENT_METHODS)[number];
