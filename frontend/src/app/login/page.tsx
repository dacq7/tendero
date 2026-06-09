"use client";

import { useState, type FormEvent } from "react";
import { login, ApiError } from "@/lib/api";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      // TODO (Fase 2): persistir sesión (cookie httpOnly / refresh) y redirigir
      // a la pantalla "Vender". Por ahora confirmamos que el flujo de auth real
      // responde y dejamos los tokens en memoria.
      await login(email, password);
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Algo salió mal. Intenta de nuevo.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen grid-cols-1 lg:grid-cols-[1.1fr_1fr]">
      <section className="relative flex flex-col justify-between overflow-hidden bg-azulon px-8 py-10 text-papel lg:px-14 lg:py-16">
        <svg
          className="pointer-events-none absolute inset-0 h-full w-full opacity-[0.07] mix-blend-soft-light"
          aria-hidden="true"
        >
          <filter id="grano">
            <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch" />
          </filter>
          <rect width="100%" height="100%" filter="url(#grano)" />
        </svg>

        <header className="relative motion-safe:animate-[fadeUp_0.6s_ease-out_both]">
          <span className="text-xs font-semibold uppercase tracking-[0.25em] text-papel/70">
            Veridis Dev
          </span>
        </header>

        <div className="relative">
          <h1 className="font-display text-6xl font-extrabold leading-[0.95] tracking-tight lg:text-7xl motion-safe:animate-[fadeUp_0.7s_ease-out_0.1s_both]">
            Tendero
          </h1>
          <span className="mt-4 block h-1.5 w-28 rounded-full bg-achiote motion-safe:animate-[grow_0.6s_ease-out_0.45s_both]" />
          <p className="mt-6 max-w-sm text-lg text-papel/80 motion-safe:animate-[fadeUp_0.7s_ease-out_0.3s_both]">
            El mostrador, sin enredos.
          </p>
        </div>

        <footer className="relative text-sm text-papel/50 motion-safe:animate-[fadeUp_0.7s_ease-out_0.5s_both]">
          Punto de venta para tiendas de barrio
        </footer>
      </section>

      <section className="flex items-center justify-center bg-papel px-6 py-12 lg:px-12">
        <div className="w-full max-w-sm motion-safe:animate-[fadeUp_0.6s_ease-out_0.4s_both]">
          <h2 className="font-display text-2xl font-bold text-tinta">Entrar</h2>
          <p className="mt-1 text-sm text-grafito">Ingresa con tu cuenta para abrir caja.</p>

          {done ? (
            <div className="mt-8 rounded-xl border border-azulon/20 bg-azulon/5 p-5">
              <p className="font-semibold text-azulon">Sesión iniciada</p>
              <p className="mt-1 text-sm text-grafito">
                El flujo de autenticación respondió correctamente. La pantalla de venta llega en la
                siguiente fase.
              </p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="mt-8 space-y-5" noValidate>
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-tinta">Correo</label>
                <input
                  id="email" type="email" autoComplete="email" required
                  value={email} onChange={(e) => setEmail(e.target.value)}
                  className="mt-1.5 h-12 w-full rounded-lg border border-niebla bg-white px-3.5 text-tinta outline-none transition focus:border-azulon focus:ring-2 focus:ring-azulon/30"
                  placeholder="tu@tienda.co"
                />
              </div>
              <div>
                <label htmlFor="password" className="block text-sm font-medium text-tinta">Contraseña</label>
                <input
                  id="password" type="password" autoComplete="current-password" required
                  value={password} onChange={(e) => setPassword(e.target.value)}
                  className="mt-1.5 h-12 w-full rounded-lg border border-niebla bg-white px-3.5 text-tinta outline-none transition focus:border-azulon focus:ring-2 focus:ring-azulon/30"
                  placeholder="••••••••"
                />
              </div>
              {error && (
                <div role="alert" className="rounded-lg border border-achiote/30 bg-achiote/10 px-3.5 py-2.5 text-sm text-achiote">
                  {error}
                </div>
              )}
              <button
                type="submit" disabled={loading}
                className="h-12 w-full rounded-lg bg-achiote font-semibold text-papel transition hover:brightness-105 focus-visible:ring-2 focus-visible:ring-achiote/40 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? "Entrando…" : "Entrar"}
              </button>
            </form>
          )}
        </div>
      </section>
    </main>
  );
}
