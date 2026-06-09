# Tendero

SaaS de punto de venta, inventario, facturación y analítica para tiendas de
barrio y pequeños comercios en Colombia (es-CO). Vertical comercial de Veridis Dev.

## Estado
Construcción por fases (ver `brief-tendero-pro.md`).
- [x] **Fase 0 — Cimientos** (completa: monorepo, Postgres, FastAPI en capas, Alembic, auth con roles, login, tests base y docs)
- [ ] Fase 1 — Inventario
- [ ] Fase 2 — Ventas + Caja + Factura interna
- [ ] Fase 3 — Pagos Wompi (sandbox)
- [ ] Fase 4 — Facturación DIAN (mock → PT)
- [ ] Fase 5 — Analítica
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

### 5. Frontend (Next.js)
```bash
cd frontend
npm install
npm run dev -- --port 3001
```
App en http://localhost:3001 · la pantalla de login está en `/login`.

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
- Dinero en enteros (centavos COP), nunca float.
- Migraciones siempre con Alembic.
- Commits convencionales (`feat:`, `fix:`, `chore:`…). Nada a "hecho" sin su test.

Para más detalle de arquitectura e invariantes, ver `CLAUDE.md` y `brief-tendero-pro.md`.
