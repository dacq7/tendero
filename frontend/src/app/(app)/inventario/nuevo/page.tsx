"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { apiGet } from "@/lib/api";
import type { Supplier } from "@/lib/types";

import AdminGuard from "../../AdminGuard";
import ProductoForm from "../ProductoForm";

export default function NuevoProductoPage() {
  const router = useRouter();
  const [proveedores, setProveedores] = useState<Supplier[]>([]);

  useEffect(() => {
    let cancel = false;
    apiGet<Supplier[]>("suppliers")
      .then((s) => !cancel && setProveedores(s))
      .catch(() => !cancel && setProveedores([]));
    return () => {
      cancel = true;
    };
  }, []);

  return (
    <AdminGuard>
      <Link href="/inventario" className="text-sm text-azulon hover:underline">
        ← Inventario
      </Link>
      <h1 className="mt-2 font-display text-2xl font-bold text-tinta">Nuevo producto</h1>
      <div className="mt-4">
        <ProductoForm proveedores={proveedores} onDone={() => router.push("/inventario")} />
      </div>
    </AdminGuard>
  );
}
