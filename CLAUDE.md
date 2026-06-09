# CLAUDE.md — Tendero

Guía para agentes (Claude Code) que trabajen en este repo. Complementa
`brief-tendero-pro.md` (la fuente de requisitos). Si algo aquí contradice una
suposición tuya, **gana esto** — son decisiones ya tomadas y verificadas en Fase 0.

## Estado
Fase 0 (Cimientos) COMPLETA: monorepo, Docker Postgres, FastAPI en capas, Alembic,
auth con roles, y frontend base con la pantalla de login. Las siguientes fases
siguen el orden de la sección 9 del brief, una por `/feature`.

## Puertos (fijados para esta máquina; NO cambiar sin actualizar este archivo)
- Postgres (Docker): **5436**
- Backend (FastAPI):  **8020**
- Frontend (Next):    **3001**
Estos puertos se eligieron por estar libres entre varios proyectos coexistentes.

## Arranque local
1. `docker compose up -d`  (Postgres 16 en 5436; healthcheck incluido)
2. Backend: `cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8020`
3. Frontend: `cd frontend && npm run dev -- --port 3001`
4. Seed del primer admin: `cd backend && python -m app.seed`
   (por defecto: admin@tendero.co / Admin1234! — SOLO desarrollo local)

## Invariantes de arquitectura (inmutables)
- **Capas backend obligatorias**: router → service → repository → model/schema.
  Toda la lógica de negocio vive en `services/`. Los routers solo orquestan y
  traducen excepciones de dominio a HTTP. Los repositories solo tocan datos.
  Ejemplo canónico ya implementado: el flujo de **auth** (copiar ese patrón).
- **Dinero en enteros** (centavos/pesos COP enteros). NUNCA float.
- **Migraciones SIEMPRE por Alembic.** Nunca tocar el esquema a mano.
  Flujo: editar modelo → `alembic revision --autogenerate -m "..."` →
  **leer la migración** → `alembic upgrade head`. Registrar cada modelo nuevo
  en `app/models/__init__.py` (si no, el autogenerate no lo ve).
- **Integraciones externas (Wompi, PT de facturación) detrás de interfaces/
  adaptadores** con implementación mock (local/test) y real (sandbox/prod),
  conmutable por env var. Aún no implementadas (Fases 3-4).
- **Idempotencia** en pagos y emisión de facturas (Fases 3-4).

## Seguridad (regla de oro)
- Secretos SOLO en `.env` (backend) y `.env.local` (frontend). NUNCA en el repo
  ni en logs. `.env.example` en la raíz es la plantilla. Verificar antes de cada
  commit que no se cuele ningún `.env` real.
- Llaves privadas (Wompi, PT) solo en el servidor. Validar firma de webhooks.
- Hashing de contraseñas: argon2 (passlib). JWT access (15 min) + refresh (7 d),
  con claim `type` que separa access de refresh.
- Datos personales conforme a Ley 1581/2012 (Habeas Data): minimizar, no exponer
  documentos de clientes sin necesidad. `UserRead` y demás DTOs de salida NUNCA
  exponen el hash ni datos sensibles.

## Stack — versiones y trampas ya resueltas (no repetir errores)
- **Next.js pineado a 16.2.8 EXACTO** (sin caret). NO flotar a `@latest`: el tag
  `latest` del registry apuntaba a una preview (16.3.0-preview) cuyo binario SWC
  no existe (404 al instalar). Regla: usar la versión estable con SWC publicado.
- **Tailwind v4**: los tokens de tema van en `src/app/globals.css` con `@theme inline`,
  NO en un `tailwind.config.ts` (no existe). Plugin: `@tailwindcss/postcss`.
- **Backend**: Python 3.12, FastAPI, SQLModel sobre SQLAlchemy 2, psycopg 3,
  Alembic, pydantic-settings. `email-validator` requerido por `EmailStr`.
- **Alembic + SQLModel**: la plantilla `alembic/script.py.mako` ya incluye
  `import sqlmodel` (necesario para columnas `AutoString`). `env.py` lee
  `DATABASE_URL` desde `app.core.config.settings`, no desde `alembic.ini`.
- **Enums**: usar `StrEnum` (Python 3.12), no `(str, Enum)`.
- **ruff**: configurado en `backend/pyproject.toml`. `B008` exceptúa `Depends`/
  `Query`/`Path`/`Body` de FastAPI. Correr `ruff check` + `ruff format` antes de commitear.
- **CORS** del backend acotado a `FRONTEND_ORIGIN` (http://localhost:3001).

## Diseño — dirección "Rótulo" (aprobada; mantener coherencia)
Esmalte de letrero sobre papel. Tokens en `frontend/src/app/globals.css`:
- `papel` #FBFBF9 (canvas) · `tinta` #16181D (texto) · `azulon` #173F8A (marca)
- `achiote` #E8552B (acción/CTA — único elemento audaz) · `niebla` #E4E1DA (bordes)
- `grafito` #5C5F66 (texto secundario)
Tipografía (next/font): **Bricolage Grotesque** (display, `--font-display`),
**Hanken Grotesk** (cuerpo, `--font-sans`), **Spline Sans Mono** (cifras, `.tabular`
con numerales tabulares — usar para TODO precio/cantidad).
Principios: "Vender" es la pantalla protagonista (legible a un brazo, toques grandes).
El dashboard de analítica es la segunda cara (denso pero claro). Estados vacíos y
errores que guían, en la voz de la interfaz (no códigos). focus visible, responsive,
`prefers-reduced-motion` respetado. La audacia se gasta en UN elemento (el ticket de
cobro, Fase 2); el resto disciplinado. Ver `SKILL_FRONTEND.md`.

## Git
Commits convencionales (`feat:`, `fix:`, `chore:`, `feat(scope):`...). Un feature
por fase, probado y commiteado antes de avanzar. Nada a "hecho" sin su test.

## Pendientes anotados en Fase 0 (no bloquean, abordar cuando toque)
- `created_at` es `timestamp without time zone` (guardamos UTC). Migrar a
  `timestamptz` en una fase futura.
- El `downgrade` de la migración inaugural no elimina el tipo enum `userrole`
  (queda huérfano en un rollback). Caso de borde; arreglo de una línea si surge.
- `npm audit` reporta 2 vulnerabilidades moderate (dev). Revisar en Fase 6
  (hardening). NUNCA correr `npm audit fix --force` a ciegas.
- Login: tras auth OK solo deja tokens en memoria (TODO marcado en
  `frontend/src/app/login/page.tsx`). Sesión real (cookie httpOnly + refresh) y
  redirección a "Vender" son Fase 2.
