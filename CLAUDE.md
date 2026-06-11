# CLAUDE.md — Tendero

Guía para agentes (Claude Code) que trabajen en este repo. Complementa
`brief-tendero-pro.md` (la fuente de requisitos). Si algo aquí contradice una
suposición tuya, **gana esto** — son decisiones ya tomadas y verificadas en Fase 0.

## Estado
Fases 0-5 COMPLETAS (todas las de negocio). Fase 0: cimientos + tests base/docs
(0.7). Fase 1: Inventario. Fase 2: Ventas + Caja + Factura interna (con frontend,
sesión real). Fase 3: Pagos Wompi sandbox (mock de demo). Fase 4: Facturación DIAN
(mock → PT). Fase 5: Analítica (seed de demo + agregaciones + dashboard). Fase 6 parte A
(bugs de Vender/Caja) y parte A.2 (UI de admin completa: inventario CRUD,
movimientos, proveedores, kardex, detalle de venta, resoluciones DIAN, historial
de cajas) COMPLETAS. Fase 5.2 (analítica profesional) COMPLETA: rentabilidad y
márgenes (matriz estrella/perro), inventario inteligente (rotación REAL en
veces/año + días de inventario + capital inmovilizado + recompra), proveedores
(compras/margen/concentración), clientes (mejores + segmento recurrente/anónimo,
documento ENMASCARADO por Habeas Data), tendencias (MoM/YoY/ticket por hora-día/
proyección). Dashboard reorganizado en pestañas con fetch lazy; CSV por sección
saneado contra inyección de fórmulas; seed de demo ampliado a 18 meses con
proveedores, clientes recurrentes y reposición proporcional al consumo. Fase 6 parte
B.1 (HARDENING DE SEGURIDAD) COMPLETA: secretos REQUERIDOS sin defaults en código
(arranque ruidoso si faltan), DTOs minimizados (sin `wompi_public_key` ni `user_id`
de cajero), anti-replay del webhook por timestamp (ventana 5 min), cabeceras de
seguridad + handler de errores que oculta trazas, rate limiting por IP en login y
webhook, y deuda de tests saldada (analítica pro por HTTP + concurrencia REAL de
`apply_movement`). Fase 6 parte B.2 (TESTS E2E con Playwright) COMPLETA: 17 e2e en
navegador real contra el stack completo (login/roles, venta efectivo→ticket, Wompi
mock aprobado/rechazado, caja+arqueo, emisión DIAN+CUFE, inventario CRUD/kardex/stock
no editable, dashboard de analítica), con base AISLADA `tendero_e2e` y puertos
dedicados (8021/3002). Queda la Fase 6 parte B.3 (deploy) — ver Pendientes.
NOTA: la analítica es de NEGOCIO, no contabilidad formal; "utilidad" = utilidad
bruta operativa estimada (venta − costo CMP), no estados financieros NIIF.

## Tests
- **Backend**: `cd backend && source .venv/bin/activate && python -m pytest`.
  Requiere Docker arriba. Usa base SEPARADA `tendero_test` (DROP/CREATE por sesión,
  `alembic upgrade head`). URL desde `TEST_DATABASE_URL` o derivada de `DATABASE_URL`
  con sufijo `_test` (obligatorio). Patrón: `backend/tests/conftest.py`.
- **Frontend**: `cd frontend && npm test` (Vitest + Testing Library, jsdom).
- **E2E (Playwright)**: `cd frontend && npm run test:e2e`. Navegador real contra el
  stack completo. Base AISLADA `tendero_e2e` (sufijo `_e2e` obligatorio; el seed la
  protege con guarda) y PUERTOS dedicados (backend **8021**, frontend **3002**) para
  no chocar con los servidores de desarrollo. Playwright levanta ambos servidores él
  mismo (`webServer`) con la env e2e (secretos de prueba del mock; `APP_ENV=test`) y
  siembra datos deterministas en `globalSetup` (`backend/app/seed_e2e.py`: admin +
  cajero `@e2e.co`, 4 productos, 1 venta histórica con factura POS-000001). Los tests
  viven en `frontend/e2e/*.e2e.ts` (Vitest los ignora); login real por la UI con
  `storageState` por rol. Serie serial (`workers:1`) por el invariante de caja única.

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
- ~~Pendiente hardening: `PaymentRead.wompi_public_key`~~: **RESUELTO en Fase 6 B.1**
  (quitada del DTO; el Widget real no está integrado). Además el webhook ahora rechaza
  replays por timestamp (ver "Fase 6 parte B.1").

## Fase 6 parte A — Bugs de Vender/Caja (corregidos)
- **Cantidad en UNIDADES**: el control del carrito suma/resta con `MILESIMAS_POR_UNIDAD`
  (1000); el input usa `step=1` y guarda contra entradas no finitas. (Causa: antes
  el input tenía `step=0.001` y operaba en milésimas.)
- **Carrito persistente**: `lib/useCart.ts` (sessionStorage) sobrevive a la navegación
  y a recargas; se limpia con `vaciar()` tras cobrar. El payload sigue sin precios.
- **Caja muestra el turno**: la pantalla consulta `cash/sessions/{id}` (totales por
  método) + `sales?cash_session_id=` (nº ventas) y calcula total del turno y esperado
  en efectivo, con botón Refrescar. (Era bug de visualización, no de datos.)
- **Vender más rápida**: grilla de productos por defecto (toque sin buscar) +
  búsqueda instantánea con debounce. `pesosToCentavos` (caja) redondea a peso entero
  antes de ×100 (sin float).

## Fase 6 parte A.2 — UI de admin completa (frontend sobre APIs existentes)
- Rutas: `/inventario` (lista con acciones admin) → `/inventario/nuevo`,
  `/inventario/[id]` (editar atributos + kardex + merma/ajuste + activar/desactivar),
  `/inventario/entradas` (entrada multilínea), `/inventario/proveedores` (CRUD);
  `/historial/[id]` (detalle de venta con snapshots + emitir DIAN); `/facturacion`
  (resoluciones DIAN). Historial de cajas cerradas en `/caja`.
- **Invariante de stock**: el stock NUNCA se edita a mano. `ProductoForm` no envía
  `stock_milesimas` (ni POST ni PATCH); en edición es solo-lectura. La carga inicial
  del alta y la merma/ajuste se registran como MOVIMIENTOS tipados.
- Conversiones puras en `lib/forms.ts` (pesos↔centavos, unidades↔milésimas, enteros).
- Gestión = solo admin: `AdminGuard` (`app/(app)/AdminGuard.tsx`) gatea las pantallas
  de escritura en el cliente (defensa en profundidad; el backend `require_role` es la
  autoridad). Nav muestra Facturación/Analítica solo a admin.

## Fase 4 — Facturación electrónica DIAN (mock → PT)
- **Mock es el camino de demo** (sin llaves): `MockFiscalProvider` genera un CUFE
  SIMULADO determinista (SHA256 de campos fiscales + secreto de prueba, SIN validez
  fiscal) y acepta/rechaza de forma explicable (rechaza si totales/IVA por tarifa no
  cuadran). `RealFiscalProvider` mapea a un PT genérico REST (Alanube/Factus),
  credenciales SOLO en server, no corre sin ellas. `FISCAL_PROVIDER=mock|real`.
  Interfaz en `services/fiscal/`. Emisión SÍNCRONA (no webhook).
- **Numeración fiscal separada del POS** (decisión confirmada): el número fiscal se
  asigna AL EMITIR del rango de una `InvoiceResolution` activa (prefijo, rango,
  vigencia, RUT, Resp. 52), con `last_numero` por resolución vía `FOR UPDATE` (sin
  huecos). El POS interno de Fase 2 queda intacto. Una sola resolución activa (índice
  parcial único). Migración `68585982b58f` siembra una resolución de demo (`SETP`).
- **`FiscalEmission`** 1:1 con `Invoice` (UNIQUE(invoice_id) = idempotencia): guarda
  número fiscal, resolución, CUFE, estado (`pending/accepted/rejected`), motivo de
  rechazo, intentos. `Invoice.dian_status`/`cufe` = caché. Reemitir una aceptada
  devuelve la misma emisión; rechazo/fallo del PT **reusa el mismo número** (no quema
  otro): el número se commitea al reservarse antes de llamar al PT.
- **Emisión manual por el admin** (no acoplada al cobro). Endpoints `/fiscal/...`:
  emit y CRUD de resoluciones = solo admin; consultar emisión = admin+cajero.
- Frontend: badge de estado DIAN + botón "Emitir a DIAN" (admin) + CUFE en historial,
  con **aviso de que la emisión real requiere habilitación** (no promete validez
  fiscal). Lógica pura en `lib/fiscal.ts`.

## Fase 5 — Analítica
- **Snapshot de costo en `SaleItem`** (`costo_unitario_snapshot_centavos`, congelado
  en `create_sale`): márgenes históricos correctos (el CMP del producto cambia con
  cada entrada). Migración `79b284eebf44` (columna + backfill + índices de ventas:
  `ix_sales_paid_at` y parcial `ix_sales_pagada_paid_at WHERE status='pagada'`).
- **Seed de demo** `python -m app.seed_demo` (separado de `app.seed`): determinista
  (PRNG sembrado + fecha de corte FIJA), idempotente (borra-y-recrea por marcadores
  `demo.`/`DEMO-`), ~1400 ventas en 9 meses con horas pico y estacionalidad,
  consistente (reutiliza `sale_pricing`). **Guarda anti-producción** (`APP_ENV`).
- **Agregaciones en backend** (`/analytics/*`, SOLO admin): summary con comparativa
  periodo anterior, timeseries (gap-filled), top productos/categorías, por método/
  cajero, horas pico, inventario (stock valorizado, rotación = COGS/stock valorizado).
  Todo entero (centavos/bps); eje temporal `paid_at` de ventas `pagada`. Cast a
  BigInteger en COGS/stock (anti-overflow int32). CSV server-side (`export.csv`,
  dataset en `Literal`). `analytics_repository` (read-only) → `analytics_service`.
- **Dashboard** `/analitica` (recharts pineado 3.8.1; nav admin-only): selector de
  rango, KPIs con delta, serie temporal, top productos, por método, inventario,
  export CSV. Lógica de rangos pura en `lib/rango.ts`.

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
5. (Opcional) Datos de demo para la analítica: `python -m app.seed_demo`
   (~1400 ventas en 9 meses; idempotente; NO correr en producción)

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
- ~~Hardening Fase 6: `config.py` tiene defaults hardcodeados para `database_url`/
  `jwt_secret`~~: **RESUELTO en Fase 6 B.1.** `database_url`, `jwt_secret`,
  `wompi_integrity_secret`, `wompi_events_secret` y `fiscal_cufe_secret` son campos
  REQUERIDOS (sin default en código): arrancar sin ellos lanza `ValidationError`. Los
  valores de prueba del mock viven en `backend/.env`/`.env.example`; la suite los
  provee como fallback solo-test en `conftest.py`. Test: `tests/test_config.py`.
- ~~Login solo en memoria~~ y ~~UI de Inventario diferida~~: **RESUELTOS en Fase 2**
  (sesión real httpOnly BFF + pantallas de inventario).
- ~~UI de inventario solo-lectura~~, ~~UI de resoluciones DIAN~~, ~~caja sin
  totales por método~~: **RESUELTOS en Fase 6 A.2** (CRUD de productos/proveedores,
  entrada/merma/ajuste, kardex, detalle de venta, resoluciones DIAN, historial de
  cajas). El stock sigue sin editarse a mano (solo por movimientos).
- `InvoiceResolutionRead` expone `last_numero` (cuántos documentos fiscales se han
  emitido) a cualquier admin. **Decisión Fase 6 B.1: se mantiene.** Es admin-only y la
  UI de facturación lo muestra a propósito ("usados hasta X"); separar un Summary
  degradaría esa pantalla sin ganancia real. Aceptado y documentado.
- Edición de resolución: la API solo permite (des)activar (`InvoiceResolutionUpdate`
  = `activa`); para cambiar rangos se crea una nueva (las resoluciones son inmutables).
  La UI refleja esto (crear+activar / activar). OK.
- ~~`ByCashierRow` expone `user_id`~~: **RESUELTO en Fase 6 B.1** (se quitó del DTO;
  el frontend no lo usaba. Solo viaja el nombre). `analytics_service.summary` llama a
  `costing.margin_bps(subtotal, cogs)` con agregados (aritméticamente correcto pero
  semánticamente la firma es unitaria — vigilar si margin_bps cambia).
- ~~`PaymentRead.wompi_public_key` viaja al cliente sin usarse~~: **RESUELTO en Fase
  6 B.1** (se quitó del DTO; el Widget real no está integrado). Cuando se integre, el
  frontend la pedirá a un endpoint propio.

## Fase 6 parte B.1 — Hardening de seguridad
- **Secretos requeridos** (`app/core/config.py`): sin defaults en código; arranque
  ruidoso. `app_env` (development|test|production) gobierna lo sensible al entorno.
  Guarda extra: en `production`, un `model_validator` RECHAZA los placeholders de demo
  (`_DEMO_SECRETS`) para que nadie despliegue con secretos públicos conocidos.
- **DTOs minimizados**: `PaymentRead` sin `wompi_public_key`; `ByCashierRow` sin
  `user_id`. Barrido confirmado: `UserRead` sin hash; `customer_doc` solo en el
  detalle de venta (dueño/admin) y ENMASCARADO en analítica (Habeas Data).
- **Anti-replay del webhook** (`payment_service.process_webhook`): además de la
  idempotencia por `event_id`, se rechaza (`WebhookReplay` → 400) todo evento fuera de
  la ventana de frescura (`_WEBHOOK_MAX_AGE_S=300`, skew futuro 60 s). El timestamp va
  firmado en el checksum; `WebhookEnvelope.timestamp` lo expone. `build_signed_event`
  usa el tiempo ACTUAL por defecto (mock/simulate generan eventos frescos).
- **Cabeceras de seguridad** (`app/core/security_headers.py`): `nosniff`,
  `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, COOP; HSTS solo en
  producción. CSP es responsabilidad del frontend (Next). CORS sigue acotado a
  `FRONTEND_ORIGIN`.
- **Handler global de errores** (`main.py`): los errores NO controlados devuelven
  `{"detail":"Error interno"}` 500; la traza solo va a logs del servidor (nunca al
  cliente). No se loguean secretos ni payloads crudos.
- **Rate limiting** (`app/core/rate_limit.py`): limitador en memoria por IP en
  `/auth/login` (10/5 min) y `/webhooks/wompi` (60/min). La IP se toma del ÚLTIMO
  salto de `X-Forwarded-For` (el que añade el PaaS de confianza; el primero lo puede
  falsear el cliente). Tope de claves (`_MAX_KEYS`) anti-DoS de memoria (fail-closed
  al saturarse). Mono-instancia (portafolio); en multi-instancia se movería a Redis
  (misma interfaz). El singleton se resetea entre tests (fixture autouse en `conftest`).
- **Mensajes genéricos** del webhook: todo rechazo (firma, replay, monto) responde el
  mismo 400 "Solicitud de webhook inválida"; el motivo no se distingue hacia fuera.
- **Tests**: `test_config.py` (arranque falla sin secretos), no-filtración en
  `test_payments.py`/`test_analytics.py`, replay en `test_payments.py`,
  `test_security_headers.py`, `test_rate_limit.py`, concurrencia REAL en
  `test_inventory_concurrency.py`. Analítica pro ya corría por HTTP.

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
