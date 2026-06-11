# Despliegue — Tendero (Railway + Vercel)

Guía para poner Tendero en producción como demo de portafolio:

- **Backend** (FastAPI) + **Postgres** → **Railway**
- **Frontend** (Next.js 16) → **Vercel**

El navegador solo habla con el frontend (Vercel); el frontend, **server-side** (BFF),
habla con el backend (Railway). Los JWT viven en cookies httpOnly del dominio de
Vercel; el navegador nunca llama directo al backend.

> **Portafolio, no producción fiscal.** Wompi y la facturación DIAN corren en modo
> `mock`: simulan el flujo completo pero **sin validez fiscal ni cobros reales**. La
> emisión real exigiría habilitación ante la DIAN y un PT autorizado.

> **Ningún secreto va en el repo.** Todos se configuran en los paneles de Railway y
> Vercel. Genera cada secreto fresco para producción con `openssl rand -hex 32`
> (no reuses los de desarrollo).

---

## 0. Pre-requisitos

- Cuenta en [Railway](https://railway.app) y en [Vercel](https://vercel.com).
- El repo en GitHub: `dacq7/tendero`.
- Generar 4 secretos (uno por cada variable marcada **[generar]** abajo):
  ```bash
  openssl rand -hex 32
  ```

---

## 1. Backend + Postgres en Railway

### 1.1 Crear el proyecto y la base
1. **New Project → Deploy from GitHub repo →** elige `dacq7/tendero`.
2. En el servicio creado: **Settings → Root Directory =** `backend`.
   (El repo es un monorepo; Railway debe construir solo `backend/`.)
3. **New → Database → Add PostgreSQL.** Railway crea la base y expone su URL como
   variable `DATABASE_URL` (referenciable con `${{Postgres.DATABASE_URL}}`).

### 1.2 Build y arranque (ya configurados en el repo)
No hay que tocar nada de esto; se incluye para que entiendas qué pasa:
- **`backend/.python-version`** (`3.12`) fija la versión de Python para Nixpacks
  (el buildpack automático de Railway).
- **`backend/requirements.txt`** trae las dependencias. `psycopg-binary` evita
  compilar nada (wheels precompiladas) — por eso no hace falta Dockerfile.
- **`backend/railway.json`** define el arranque: `sh start.sh`.
- **`backend/start.sh`** corre **`alembic upgrade head`** (migra el esquema) y luego
  **`uvicorn app.main:app --host 0.0.0.0 --port $PORT`**. Si la migración falla, el
  server NO arranca (deploy ruidoso). Railway inyecta `$PORT`.

### 1.3 Variables de entorno (Railway → Variables)
| Variable | Valor | Nota |
|---|---|---|
| `APP_ENV` | `production` | Activa HSTS y la guarda anti-secretos-de-demo. |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | La inyecta el plugin Postgres. El backend normaliza el driver a `postgresql+psycopg://` solo. |
| `JWT_SECRET` | **[generar]** | Raíz de confianza de la sesión. |
| `FRONTEND_ORIGIN` | `https://<tu-app>.vercel.app` | El dominio de Vercel (lo sabrás tras el paso 2). Admite varios separados por coma. |
| `WOMPI_PROVIDER` | `mock` | Portafolio. |
| `WOMPI_PUBLIC_KEY` | `pub_test_demo` | Pública, no es secreto. |
| `WOMPI_INTEGRITY_SECRET` | **[generar]** | Requerido aunque sea mock. |
| `WOMPI_EVENTS_SECRET` | **[generar]** | Requerido aunque sea mock. |
| `FISCAL_PROVIDER` | `mock` | Portafolio. |
| `FISCAL_CUFE_SECRET` | **[generar]** | Requerido aunque sea mock. |
| `JWT_ACCESS_TTL_MIN` | `15` | Opcional (default 15). |
| `JWT_REFRESH_TTL_DAYS` | `7` | Opcional (default 7). |
| `PORT` | _(la inyecta Railway)_ | No la definas tú. |

> Si omites cualquier secreto requerido, el backend **falla al arrancar** con un
> error claro (hardening Fase 6 B.1). Si reusas un secreto de demo conocido con
> `APP_ENV=production`, también aborta. Es a propósito.

> En la primera pasada quizá no sepas aún el dominio de Vercel: pon un placeholder en
> `FRONTEND_ORIGIN` y ajústalo en el paso 3.

### 1.4 Exponer el dominio
**Settings → Networking → Generate Domain.** Copia la URL pública del backend
(`https://<backend>.up.railway.app`); la usarás en Vercel (`BACKEND_URL`).

### 1.5 Crear el primer admin (una sola vez)
Desde la **shell del servicio** en Railway (o un comando one-off del CLI), con una
contraseña FUERTE (no la default de desarrollo):
```bash
python -m app.seed admin@tudominio.co 'TuClaveFuerte!' 'Tu Nombre'
```

### 1.6 (Opcional) Poblar la demo de analítica
Para que el dashboard se vea con datos, corre el seed de demo. La guarda de seguridad
**rechaza `APP_ENV=production`** (borra y recrea datos), así que se invoca declarando
explícitamente que NO es contra producción real, con un `APP_ENV` distinto **solo
para esa ejecución**:
```bash
APP_ENV=demo python -m app.seed_demo
```
> Genera ~1400 ventas en 18 meses. Es idempotente (borra-y-recrea el dataset `demo.`).
> NO lo corras si la base tuviera datos reales que conservar.

### 1.7 Verificar el backend
`https://<backend>.up.railway.app/health` debe responder
`{"status":"ok","database":"up"}`.

---

## 2. Frontend en Vercel

1. **Add New → Project → Import** `dacq7/tendero`.
2. **Root Directory =** `frontend`. Vercel detecta Next.js 16 automáticamente
   (build `next build`, sin overrides).
3. **Environment Variables:**

| Variable | Valor | Nota |
|---|---|---|
| `BACKEND_URL` | `https://<backend>.up.railway.app` | **Server-only** (no `NEXT_PUBLIC_*`): lo usa el BFF para hablar con Railway. |

> `NODE_ENV=production` lo pone Vercel solo → las cookies de sesión salen con
> `secure` (HTTPS). No definas `NEXT_PUBLIC_API_URL` (es legado, el código no la usa).

4. **Deploy.** Copia el dominio resultante (`https://<tu-app>.vercel.app`).

---

## 3. Post-deploy (el orden importa)

1. **Cerrar CORS al dominio real.** En Railway, ajusta `FRONTEND_ORIGIN` al dominio
   de Vercel del paso 2 (`https://<tu-app>.vercel.app`). Si quieres que las **previews**
   de Vercel también funcionen, añade sus orígenes separados por coma, o pide habilitar
   el regex de previews (ver nota abajo). Railway redepliega el backend solo.
2. **Verificación end-to-end en producción** (manual, en el dominio de Vercel):
   - Inicia sesión con el admin sembrado (1.5).
   - Abre caja → haz una venta en efectivo → ve el ticket con número de factura.
   - En Historial, emite una factura a DIAN (mock) → estado **Aceptada** + CUFE.
   - Abre Analítica → KPIs y pestañas cargan (con datos si corriste 1.6).
   - (Opcional) Crea un cajero para probar el guard de roles. El alta de usuarios es
     SOLO por script (no hay endpoint de registro): adapta `app/seed.py` o añade un
     pequeño comando que cree un `User` con `role=cajero`. Confirma que ese cajero NO
     ve Analítica/Facturación.

> **Previews de Vercel (opt-in).** Los dominios de preview son subdominios
> impredecibles (`*.vercel.app`). Por seguridad, por defecto solo se listan orígenes
> explícitos en `FRONTEND_ORIGIN`. Si necesitas CORS para todas las previews, se puede
> habilitar `allow_origin_regex` (`https://.*\.vercel\.app`) en
> `backend/app/main.py`; queda como cambio opt-in para no abrir CORS a cualquier
> proyecto alojado en `vercel.app`.

---

## 4. Resumen de variables

**Railway (backend):** `APP_ENV`, `DATABASE_URL`*, `JWT_SECRET`, `FRONTEND_ORIGIN`,
`WOMPI_PROVIDER`, `WOMPI_PUBLIC_KEY`, `WOMPI_INTEGRITY_SECRET`, `WOMPI_EVENTS_SECRET`,
`FISCAL_PROVIDER`, `FISCAL_CUFE_SECRET` (+ `PORT`*).
**Vercel (frontend):** `BACKEND_URL` (+ `NODE_ENV`* lo pone Vercel).
_(* = inyectadas por la plataforma; no las defines a mano.)_

El desarrollo local no cambia: sigue con `docker compose up -d`, el backend en 8020 y
el frontend en 3001 leyendo de `backend/.env` y `frontend/.env.local`.
