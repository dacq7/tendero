"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { apiGet, logout } from "@/lib/api";
import type { UserMe } from "@/lib/types";

const NAV = [
  { href: "/vender", label: "Vender" },
  { href: "/caja", label: "Caja" },
  { href: "/inventario", label: "Inventario" },
  { href: "/historial", label: "Historial" },
  { href: "/facturacion", label: "Facturación", adminOnly: true },
  { href: "/analitica", label: "Analítica", adminOnly: true },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<UserMe | null>(null);

  useEffect(() => {
    apiGet<UserMe>("auth/me")
      .then(setUser)
      .catch(() => router.replace("/login"));
  }, [router]);

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-10 border-b border-niebla bg-papel/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <div className="flex items-center gap-6">
            <Link href="/vender" className="font-display text-xl font-extrabold text-azulon">
              Tendero
            </Link>
            <nav className="flex gap-1">
              {NAV.filter((item) => !item.adminOnly || user?.role === "admin").map((item) => {
                const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    className={`rounded-md px-3 py-2 text-sm font-medium transition ${
                      active
                        ? "bg-azulon/10 text-azulon"
                        : "text-grafito hover:bg-niebla/60 hover:text-tinta"
                    }`}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>
          <div className="flex items-center gap-3 text-sm">
            {user && (
              <span className="hidden text-grafito sm:inline">
                {user.full_name} · <span className="capitalize">{user.role}</span>
              </span>
            )}
            <button
              onClick={handleLogout}
              className="rounded-md border border-niebla px-3 py-1.5 font-medium text-tinta transition hover:bg-niebla/60"
            >
              Salir
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">{children}</main>
    </div>
  );
}
