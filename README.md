# Tendero

SaaS de punto de venta, inventario, facturación y analítica para tiendas de
barrio y pequeños comercios en Colombia (es-CO). Vertical comercial de Veridis Dev.

## Estado
Construcción por fases (ver `brief-tendero-pro.md`).
- [x] **Fase 0 — Cimientos** (monorepo, Postgres, FastAPI en capas, Alembic, auth con roles, login, tests base y docs)
- [x] **Fase 1 — Inventario** (productos, proveedores, kardex, costeo CMP, alertas)
- [x] **Fase 2 — Ventas + Caja + Factura interna** (venta atómica, numeración propia, caja con arqueo, sesión real httpOnly + UI "Vender")
- [x] **Fase 3 — Pagos Wompi (sandbox)** (interfaz mock/real, webhook idempotente con firma, flujo de pago asíncrono; mock como demo)
- [x] **Fase 4 — Facturación DIAN (mock → PT)** (interfaz mock/real, resolución de numeración, CUFE simulado, emisión idempotente; sin validez fiscal real)
- [x] **Fase 5 — Analítica** (seed de demo determinista, agregaciones admin-only en backend, dashboard con recharts y export CSV)
- [ ] Fase 6 — Pulido + deploy

## Puertos locales (fijados para esta máquina)
| Servicio            | Puerto |
|---------------------|--------|
| Postgres (Docker)   | 5436   |
| Backend (FastAPI)   | 8020   |
| Frontend (Next.js)  | 3001   |

## Stack
- Frontend: Next.js 16 (App Router) + TypeScript + Tailwind v4
- Backend: Python 3.12 + FastAPI en capas (routers → services → repositories → models/schemas), SQLModel/SQLAlchemy 2, psycopg 3
- DB: PostgreSQL 16 (Docker) + Alembic
- Auth: JWT (access 15 min + refresh 7 d), hashing argon2

## Requisitos previos
- Docker + Docker Compose
- Python 3.12
- Node.js 20+ y npm

## Arranque local (end-to-end)

### 1. Variables de entorno
`.env.example` (raíz) es la plantilla. Copia las secciones que correspondan:

```bash
cp .env.example backend/.env          # vars de backend + DB
cp .env.example frontend/.env.local   # deja solo las NEXT_PUBLIC_*
```

Genera un `JWT_SECRET` real en `backend/.env`:

```bash
openssl rand -hex 32
```

> **Secretos requeridos (hardening Fase 6 B.1).** El backend ya **no** trae valores
> por defecto para los secretos: si faltan en `backend/.env`, arranca con un
> `ValidationError` claro en vez de usar credenciales conocidas. Asegúrate de definir
> en `backend/.env` al menos: `DATABASE_URL`, `JWT_SECRET`, `WOMPI_INTEGRITY_SECRET`,
> `WOMPI_EVENTS_SECRET`, `FISCAL_CUFE_SECRET` (los tres últimos pueden ser los valores
> de prueba del modo `mock`). En `production`, pon `APP_ENV=production` (activa HSTS) y
> reemplaza TODOS los secretos por valores reales. La suite de tests provee los
> secretos de prueba del mock como fallback (`backend/tests/conftest.py`), así que
> solo necesita `DATABASE_URL` y `JWT_SECRET` en `backend/.env`.

> Los `.env` reales **nunca** se suben al repo (ya están en `.gitignore`).

### 2. Base de datos (Postgres en Docker)
```bash
docker compose up -d        # Postgres 16 en el puerto 5436 (con healthcheck)
```

### 3. Backend (FastAPI)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head        # aplica las migraciones
uvicorn app.main:app --reload --port 8020
```
API en http://localhost:8020 · documentación en http://localhost:8020/docs

### 4. Seed del primer admin
Con el backend ya migrado (paso 3), en otra terminal:
```bash
cd backend && source .venv/bin/activate
python -m app.seed          # admin@tendero.co / Admin1234!  (SOLO desarrollo)
```
Acepta argumentos: `python -m app.seed <email> <password> <nombre>`. Es idempotente.

**Datos de demo para la analítica** (opcional, recomendado para ver el dashboard):
```bash
cd backend && source .venv/bin/activate
python -m app.seed_demo   # ~1400 ventas en 9 meses, idempotente. NO en producción.
```

### 5. Frontend (Next.js)
```bash
cd frontend
npm install
npm run dev -- --port 3001
```
App en http://localhost:3001 · login en `/login` · mostrador en `/vender`.

La sesión es real: el login (`/api/session`) guarda los JWT en **cookies httpOnly**
y el navegador habla con el backend solo a través del proxy server-side
(`/api/proxy/...`). Por eso `frontend/.env.local` necesita `BACKEND_URL`
(server-side; los JWT nunca llegan al navegador). Entra con el admin sembrado en el
paso 4. Rutas protegidas: `/vender`, `/caja`, `/inventario`, `/historial`.

## Tests

### Backend (pytest)
Usa una base de datos **separada y aislada** (`tendero_test`) en el mismo Postgres
de Docker; aplica las migraciones reales (`alembic upgrade head`) y la crea/elimina
por sesión de test. Nunca toca la base de desarrollo.

```bash
cd backend && source .venv/bin/activate
docker compose up -d        # requiere Postgres arriba
python -m pytest
```
La URL de test se deriva de `DATABASE_URL` añadiendo el sufijo `_test`; puedes
sobreescribirla con la variable de entorno `TEST_DATABASE_URL`.

### Frontend (Vitest)
```bash
cd frontend
npm test                    # una pasada (CI)
npm run test:watch          # modo watch
```

## Reglas
- Secretos solo en `.env` / `.env.local` (nunca en el repo). Ver `.env.example`.
  Son **requeridos**: sin ellos el backend no arranca (no hay defaults en código).
- Dinero en enteros (centavos COP), nunca float.
- Migraciones siempre con Alembic.
- Commits convencionales (`feat:`, `fix:`, `chore:`…). Nada a "hecho" sin su test.

## Endurecimiento de seguridad (Fase 6 B.1)
- **Secretos requeridos**: arranque ruidoso si falta cualquiera (no credenciales por defecto).
- **Cabeceras de seguridad** en toda respuesta (`nosniff`, anti-frame, `Referrer-Policy`,
  COOP; HSTS solo con `APP_ENV=production`). CSP la maneja el frontend.
- **Rate limiting** por IP en `/auth/login` (10/5 min) y `/webhooks/wompi` (60/min).
- **Anti-replay del webhook**: además de la idempotencia por evento, se rechazan eventos
  fuera de una ventana de frescura de 5 min (con tolerancia de reloj).
- **Errores no controlados** devuelven un cuerpo genérico; la traza solo va a los logs
  del servidor, nunca al cliente. CORS acotado al origen del frontend.

Para más detalle de arquitectura e invariantes, ver `CLAUDE.md` y `brief-tendero-pro.md`.
