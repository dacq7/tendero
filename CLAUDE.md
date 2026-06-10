# CLAUDE.md — Tendero

Guía para agentes (Claude Code) que trabajen en este repo. Complementa
`brief-tendero-pro.md` (la fuente de requisitos). Si algo aquí contradice una
suposición tuya, **gana esto** — son decisiones ya tomadas y verificadas en Fase 0.

## Estado
Fases 0, 1, 2 y 3 COMPLETAS. Fase 0: cimientos + tests base y docs (0.7). Fase 1:
Inventario (backend). Fase 2: Ventas + Caja + Factura interna (backend y frontend,
incl. sesión real y UI de Inventario). Fase 3: Pagos Wompi sandbox (backend y
frontend, modo mock como camino de demo). Siguiente: Fase 4 (Facturación DIAN
mock → PT). Las fases siguen la sección 9 del brief, una por `/feature`.

## Tests
- **Backend**: `cd backend && source .venv/bin/activate && python -m pytest`.
  Requiere Docker arriba. Usa base SEPARADA `tendero_test` (DROP/CREATE por sesión,
  `alembic upgrade head`). URL desde `TEST_DATABASE_URL` o derivada de `DATABASE_URL`
  con sufijo `_test` (obligatorio). Patrón: `backend/tests/conftest.py`.
- **Frontend**: `cd frontend && npm test` (Vitest + Testing Library, jsdom).

## Fase 1 — Inventario
- Modelos: `Supplier`, `Product`, `InventoryMovement` (kardex). Enums `IvaRate`
  (exento/0/5/19), `ProductUnit`, `MovementType`.
- **Decisiones bloqueadas**: costeo = **promedio ponderado (CMP)** en `services/costing.py`;
  stock **persistido** y mutado SOLO por `inventory_service.apply_movement` (kardex
  auditable con `stock_resultante`); IVA = **enum cerrado**; cantidades en **milésimas**
  enteras (1000 = 1 unidad), dinero en **centavos**. Márgenes en **bps enteros** (no float).
- Stock con `SELECT FOR UPDATE` (`product_service.get_locked`) para evitar carreras.
  Entrada de mercancía multilínea **atómica** (un solo commit). Permisos: admin escribe,
  cajero consulta. Endpoints bajo `/products`, `/suppliers`, `/inventory`.
- Migración `c025802323ed`.

## Fase 2 — Ventas + Caja + Factura interna
- Modelos: `Sale` + `SaleItem` (snapshot de precio/IVA por línea, sin referencia
  viva), `Invoice` (numeración propia; `dian_status=none`, cufe/wompi nulos hasta
  Fases 3-4), `InvoiceSequence`, `CashRegisterSession`. Migración `4c84926354df`.
- **Decisiones bloqueadas**: precio = **base sin IVA** (total = subtotal + IVA),
  pricing puro en `services/sale_pricing.py` + `services/money.py` (half-up entero,
  compartido con costing); numeración **serie global única `POS`** con `SELECT FOR
  UPDATE` en la txn de la venta (sin huecos ni duplicados; mapea a resolución DIAN);
  **caja única a la vez como VALIDACIÓN de negocio** (advisory lock + check, NO
  constraint estructural — `CashRegisterSession.user_id` deja la puerta a multi-caja);
  **venta requiere caja abierta**. Anulación: enum previsto, sin endpoint (fase futura).
- **Venta atómica** (`sale_service.create_sale`, un commit): descuenta stock vía
  `apply_movement` (FOR UPDATE por producto), congela snapshots, totales/IVA, asigna
  número, marca pagada. Rollback total ante fallo (no consume stock ni número).
- Permisos: cajero opera ventas/su caja y ve **solo lo suyo** (ventas, facturas y
  detalle de caja filtrados por dueño); admin todo. Endpoints `/sales`, `/cash`,
  `/invoices`.
- **Frontend — sesión real (BFF)**: los JWT viven SOLO en cookies httpOnly; el
  navegador habla con Route Handlers mismo-origen (`/api/session`, `/api/proxy/[...]`)
  que adjuntan el token server-side y refrescan en 401. `src/proxy.ts` protege rutas
  (convención `proxy` de Next 16, no `middleware`). El proxy tiene **allowlist** de
  prefijos (anti-SSRF). `BACKEND_URL` es server-only (no `NEXT_PUBLIC_*`).
- Pantallas (dirección "Rótulo"): **Vender** (protagonista: buscador, carrito,
  totales/IVA en vivo, cobro y **ticket** = elemento audaz), **Caja** (abrir/cerrar
  con arqueo), **Inventario** (lista + alertas), **Historial** (facturas).
- Tests: backend (venta atómica/rollback, numeración SIN duplicados bajo
  **concurrencia real**, IVA/totales, arqueo, permisos por dueño); frontend Vitest
  (carrito/dinero puro, login, flujo de venta carrito→cobro→ticket).

## Fase 3 — Pagos Wompi (sandbox)
- **Mock es el camino principal de demo** (sin llaves): `MockWompiProvider` con
  firmas SHA256 REALES contra secretos de prueba. `RealWompiProvider` existe y mapea
  al API real (Widget; llave privada solo en server) pero no corre sin llaves.
  Conmutable por `WOMPI_PROVIDER=mock|real`. Interfaz en `services/payments/`.
- **Flujo async (rediseño confirmado)**: la venta por tarjeta/PSE/Nequi nace
  `pendiente_pago` y RESERVA stock al crear; la factura se numera y la venta se marca
  `pagada` SOLO cuando el webhook confirma (approved). Rechazo → `rechazada` + reverso
  de stock (`MovementType.reverso_venta`, suma sin recostear) y NO consume número.
  Efectivo/transferencia siguen el cobro local síncrono de Fase 2 (intacto).
- **Webhook idempotente** (`/webhooks/wompi`, público, sin auth): valida firma
  (timing-safe, allowlist de propiedades), coteja monto+referencia contra el Payment,
  y usa `webhook_events UNIQUE(provider,event_id)` con SAVEPOINT como candado (resiste
  concurrencia). Modelos `Payment`, `WebhookEvent`. Migración `9a1dd4b41864`.
- `/payments` inicia el pago (idempotente por venta); `/payments/{id}/simulate` solo
  en mock (cierra el ciclo en demo con firma válida). `SaleRead.invoice` es opcional.
  Cierre de caja bloquea si hay ventas `pendiente_pago` en vuelo.
- Frontend: Vender refleja el estado async (cobrar → **procesando** → ticket/rechazado),
  con polling en real y botones de simulación en mock. Lógica pura en `lib/cobro.ts`.

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
- Hardening Fase 6: `app/core/config.py` tiene defaults hardcodeados para
  `database_url` y `jwt_secret`. Arrancar sin `.env` usa credenciales conocidas en
  silencio. Hacerlos campos requeridos (sin default) para que falle ruidosamente.
- ~~Login solo en memoria~~ y ~~UI de Inventario diferida~~: **RESUELTOS en Fase 2**
  (sesión real httpOnly BFF + pantallas de inventario).
- Inventario en UI es de solo-lectura por ahora: los formularios de alta/edición de
  productos y proveedores y la entrada de mercancía existen en la **API** (Fase 1)
  pero aún no tienen pantalla de escritura (admin). Abordar cuando se priorice.
- Caja: el arqueo concilia efectivo; los totales por otros métodos se exponen
  (`/cash/sessions/{id}` → `totales_por_metodo`) pero la UI de caja aún no los pinta.

## Contexto de portafolio (orienta Fases 3-6)
Este es un proyecto de PORTAFOLIO. No habrá credenciales reales de Wompi, del PT de
facturación, ni cuentas pagas. El objetivo es demostrar dominio profesional, no operar
un comercio real. En consecuencia:

- **Integraciones externas (Wompi, FiscalProvider): el modo `mock` es el camino
  principal de demostración.** Los mocks deben simular el flujo COMPLETO y realista:
  estados (pending → accepted/rejected), CUFE/referencia simulados, webhook entrante
  que actualiza estado de forma idempotente, firma de integridad calculada (contra un
  secreto de prueba). Que se vea el flujo de mostrador entero de principio a fin.
- **La implementación `real` (RealWompiProvider, RealFiscalProvider) debe EXISTIR y
  estar bien diseñada** (mapea al API real, llave privada solo en servidor, conmutable
  por env var), pero no se ejecuta sin credenciales. Lo que demuestra seniority es la
  calidad de la interfaz/adaptador, no tener la llave.
- **No prometer validez fiscal.** Dejar claro (README/UI) que la emisión real requiere
  habilitación del comercio ante la DIAN y un PT autorizado. El software está *listo
  para integrarse*.
- **Seed de datos de demostración (importante para Fase 5):** crear un seed que genere
  cientos de ventas ficticias repartidas en semanas/meses, con variedad de productos,
  métodos de pago, cajeros y horas, para que el dashboard de analítica (márgenes,
  ticket promedio, rotación, horas pico, series temporales) se vea POBLADO y creíble,
  no vacío. Un comando idempotente, separado del seed del admin.
- **Deploy (Fase 6): preferir planes gratuitos** (Vercel free + Railway free) para
  tener un enlace en vivo. Si no es viable, documentar arranque local impecable.
