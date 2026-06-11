<div align="center">

# Tendero

### Punto de venta, inventario, facturación y analítica para tiendas de barrio en Colombia

Plataforma SaaS full-stack que cubre el ciclo completo del comercio minorista colombiano — venta en mostrador, inventario auditable con kardex, facturación con numeración secuencial y estado DIAN, pagos vía Wompi, y analítica de negocio de nivel profesional.

**Next.js · TypeScript · FastAPI · PostgreSQL · SQLModel · Alembic · Tailwind CSS · Playwright · Railway · Vercel**

**[Demo en vivo](https://tendero-beta.vercel.app) · [Ver código](https://github.com/dacq7/tendero)**

</div>

---

## ¿Qué es esto?

Las tiendas de barrio y pequeños comercios en Colombia operan con una complejidad que los POS genéricos no resuelven bien: manejan IVA por producto (exento, 5%, 19%), venden en unidades fraccionadas, cobran en efectivo y por Nequi/PSE/tarjeta, y —si quieren formalizarse— necesitan facturación electrónica con numeración autorizada por la DIAN y un proveedor tecnológico.

Tendero está construido para ese flujo real. Un cajero abre su caja, vende desde una grilla de productos pensada para el mostrador, cobra (en efectivo o por Wompi), y cada venta genera una factura con numeración secuencial sin huecos. El administrador gestiona el inventario mediante movimientos auditables —nunca editando el stock a mano—, configura su resolución DIAN, y analiza el negocio con un dashboard que responde las preguntas que un dueño de tienda realmente se hace: qué productos dejan utilidad, cuánto capital tiene dormido en inventario, de qué proveedores depende, y quiénes son sus mejores clientes.

El resultado es un sistema que refleja cómo funciona de verdad una tienda colombiana — no una prueba de concepto, sino una herramienta funcional.

> **Portafolio, no producción fiscal.** Las integraciones de pagos (Wompi) y facturación electrónica (DIAN) corren en **modo mock**: simulan el flujo completo de extremo a extremo —incluyendo firma de webhooks, idempotencia, estados y CUFE— pero sin cobros reales ni validez fiscal. La emisión real exige la habilitación del comercio ante la DIAN y un Proveedor Tecnológico autorizado. La arquitectura está *lista para integrarse*: cada proveedor externo vive detrás de una interfaz conmutable mock/real por variable de entorno.

---

## Demo en vivo

**[tendero-beta.vercel.app](https://tendero-beta.vercel.app)**

| Rol | Email | Contraseña | Qué puede ver |
|-----|-------|-----------|---------------|
| **Administrador** | `admin@tendero.co` | `Demo.Admin2026` | Todo: inventario, facturación, analítica, gestión |
| **Cajero** | `cajero@tendero.co` | `Demo.Caja2026` | Solo operación de mostrador: vender, caja, consultar |

La base de demo está poblada con **~2.770 ventas a lo largo de 18 meses**, 28 productos de tienda de barrio, 5 proveedores, 3 cajeros y 10 clientes recurrentes — suficiente historia para que la analítica (comparativas año contra año, rotación, tendencias) tenga datos reales que mostrar.

> Inicia sesión como **cajero** para ver el producto desde el mostrador; entra como **administrador** para ver la analítica y la gestión completa. El menú se adapta al rol.

---

## Características principales

| 🛒 Venta y Caja | 📦 Inventario | 📊 Analítica de negocio |
|---|---|---|
| Pantalla de venta optimizada para mostrador | Kardex auditable por producto | Matriz volumen × margen (estrella / perro) |
| Carrito persistente entre navegación | Movimientos tipados: entrada, merma, ajuste | Rentabilidad por producto y categoría |
| Cobro en efectivo o vía Wompi | Costeo promedio ponderado (CMP) | Rotación de inventario y días de stock |
| Apertura/cierre de caja con arqueo | Stock nunca editable a mano (integridad) | Capital inmovilizado y sugerencia de recompra |
| Totales por método de pago en vivo | IVA por producto (exento / 5% / 19%) | Compras, margen y concentración por proveedor |
| Cantidades en unidades o fraccionadas | Alertas de stock bajo | Mejores clientes y segmentación |
| Ticket con número de factura | Gestión de proveedores | Crecimiento mes a mes y año contra año |

| 🧾 Facturación | 💳 Pagos | 🔐 Seguridad y roles |
|---|---|---|
| Numeración secuencial sin huecos | Flujo Wompi async (procesando → aprobado) | Roles admin / cajero con guards de servidor |
| Estado DIAN (pendiente / aceptada / rechazada) | Webhook idempotente con firma verificada | JWT en cookies httpOnly (nunca en el navegador) |
| CUFE determinista por factura | Reverso de stock ante rechazo | Secretos requeridos: la app no arranca sin ellos |
| Resoluciones DIAN configurables | Idempotencia por evento (anti-duplicado) | Rate limiting en login y webhook |
| Emisión a DIAN desde el detalle de venta | Anti-replay por ventana de tiempo | Minimización de datos personales (Habeas Data) |

---

## Capturas

### Pantalla de venta — el corazón del producto
![Pantalla de venta](docs/screenshots/02-vender.png)
*Grilla de productos para agregar con un toque, carrito persistente y cálculo de IVA en vivo. Pensada para uso real en mostrador.*

### Analítica — rentabilidad por producto
![Matriz estrella/perro](docs/screenshots/09-analitica-rentabilidad.png)
*Matriz volumen × margen con cuadrantes calculados por la mediana del dataset (sin umbrales arbitrarios): identifica de un vistazo qué productos venden y dejan utilidad ("estrellas") frente a los que no aportan a ninguno de los dos ejes ("perros").*

### Dashboard — resumen del negocio
![Dashboard resumen](docs/screenshots/08-analitica-resumen.png)
*KPIs con comparativa contra el periodo anterior, serie temporal, productos top y ventas por método de pago.*

<details>
<summary><b>Ver más capturas</b></summary>

| | |
|---|---|
| ![Login](docs/screenshots/01-login.png) **Login** | ![Caja](docs/screenshots/03-caja.png) **Caja con arqueo** |
| ![Inventario](docs/screenshots/04-inventario.png) **Inventario** | ![Kardex](docs/screenshots/05-kardex.png) **Kardex por producto** |
| ![Detalle de venta](docs/screenshots/06-historial-detalle.png) **Detalle de venta** | ![DIAN](docs/screenshots/07-dian.png) **Factura emitida a DIAN** |
| ![Inventario inteligente](docs/screenshots/10-analitica-inventario.png) **Inventario inteligente** | |

</details>

---

## Stack técnico

| Capa | Tecnología |
|------|-----------|
| **Backend** | Python 3.12 + FastAPI, arquitectura en capas (router → service → repository → model/schema) |
| **ORM / DB** | SQLModel + SQLAlchemy 2 sobre PostgreSQL 16, driver psycopg 3 |
| **Migraciones** | Alembic (versionadas desde el día uno; el esquema nunca se toca a mano) |
| **Autenticación** | JWT access (15 min) + refresh (7 días), hashing argon2, guards por rol |
| **Frontend** | Next.js 16 (App Router) + TypeScript + Tailwind CSS v4 |
| **Sesión** | BFF con proxy server-side; JWT en cookies httpOnly, nunca expuesto al navegador |
| **Gráficas** | Recharts |
| **Pagos** | Wompi (interfaz mock/real conmutable), webhook idempotente con firma |
| **Facturación** | Proveedor fiscal DIAN (interfaz mock/real conmutable), CUFE y estado por factura |
| **Pruebas** | pytest (172) · Vitest (67) · Playwright e2e (17) — 256 pruebas |
| **Hosting** | Backend + PostgreSQL en Railway · Frontend en Vercel |

---

## Decisiones de arquitectura

**El dinero nunca es float.** Todos los montos se manejan en enteros (centavos de COP) y los márgenes en puntos básicos (bps). Las cantidades se almacenan en milésimas (1000 = 1 unidad) para soportar venta fraccionada sin errores de redondeo. Esta invariante se valida en la suite de pruebas.

**El stock se mueve, no se edita.** El inventario nunca se modifica con un campo editable —eso rompería la auditoría—. Todo cambio de stock ocurre mediante un movimiento tipado (entrada, merma, ajuste) que queda registrado en el kardex, y el costo promedio ponderado se recalcula en cada entrada. El formulario de producto expone el stock como solo-lectura; las pruebas verifican que ningún payload pueda alterarlo directamente.

**Integraciones externas detrás de interfaces conmutables.** Wompi (pagos) y el proveedor fiscal DIAN viven cada uno detrás de una interfaz con dos implementaciones —`mock` para desarrollo y demo, `real` para producción— intercambiables por variable de entorno. Esto permite construir y probar todo el flujo (firma de webhooks, idempotencia, estados, CUFE) sin credenciales reales, y cambiar a producción sin reescribir lógica de negocio.

**Numeración de facturas sin huecos.** Las facturas se numeran secuencialmente bajo un bloqueo a nivel de fila (`FOR UPDATE`), garantizando que no haya saltos ni duplicados incluso con ventas concurrentes. La resolución DIAN (rango autorizado) se maneja por separado de la numeración interna del POS.

**Idempotencia en pagos y emisión fiscal.** Los webhooks de pago y las emisiones a DIAN son idempotentes: un evento repetido (reintento de la pasarela, doble clic) nunca produce un cobro o una factura duplicada. Se refuerza con restricciones únicas por evento, bloqueos a nivel de fila y protección anti-replay por ventana de tiempo.

**Aislamiento de la sesión.** El JWT nunca llega al navegador. El frontend habla con un BFF (Backend-for-Frontend) en Next.js que guarda el token en una cookie httpOnly y actúa como proxy hacia el backend. El navegador solo ve su propio dominio.

**Minimización de datos personales (Ley 1581 / Habeas Data).** La analítica de clientes agrupa por documento sin persistir una tabla de datos personales, y el documento se enmascara en toda salida. Se captura lo mínimo necesario para la factura, nada más.

---

## Analítica de negocio

A diferencia de un dashboard que solo cuenta ventas, Tendero responde preguntas de decisión:

- **Rentabilidad real:** margen bruto por producto y categoría, contribución de cada producto a la utilidad (no solo a las ventas), y una matriz volumen × margen que clasifica el catálogo en estrella / tirón / nicho / perro según las medianas del propio negocio.
- **Inventario inteligente:** rotación anualizada (veces/año), días de inventario, capital inmovilizado (stock que no rota en 180+ días), quiebres de stock y sugerencias de recompra.
- **Proveedores:** compras y margen aportado por cada uno, y concentración (qué porcentaje de las compras depende de pocos proveedores) — un indicador de riesgo operativo.
- **Clientes:** mejores clientes por gasto y frecuencia, y segmentación entre recurrentes y consumidor final.
- **Tendencias:** crecimiento mes a mes, comparativa año contra año, ticket promedio por hora del día y día de la semana, y proyección del periodo en curso.

Todas las agregaciones se calculan en el backend (nunca en el cliente), en enteros, y cada una está verificada contra datos controlados en la suite de pruebas. Cada sección exporta a CSV.

---

## Pruebas

```
Backend (pytest):   172 pruebas
Frontend (Vitest):   67 pruebas
End-to-end (Playwright): 17 pruebas
─────────────────────────────────
Total:              256 pruebas
```

Las pruebas e2e con Playwright recorren los flujos críticos en un navegador real contra el stack completo (frontend + backend + PostgreSQL): autenticación y roles, venta en efectivo completa (caja → carrito → cobro → ticket → historial), pago asíncrono con Wompi (aprobado y rechazado con reverso de stock), flujo de inventario (crear → entrada → merma → kardex), emisión a DIAN, y carga del dashboard de analítica.

La cobertura de backend se concentra donde el riesgo es mayor: todo lo que toca dinero, stock, numeración de facturas, idempotencia de pagos y emisión fiscal, agregaciones de analítica y permisos por rol.

---

## Estructura del proyecto

```
tendero/
├── backend/                  # FastAPI + SQLModel + Alembic
│   ├── app/
│   │   ├── routers/          # Endpoints HTTP por dominio
│   │   ├── services/         # Lógica de negocio (toda aquí), incluidos
│   │   │                     #   los proveedores Wompi y fiscal (mock/real)
│   │   ├── repositories/     # Acceso a datos
│   │   ├── models/           # Modelos SQLModel
│   │   ├── schemas/          # DTOs de entrada/salida
│   │   ├── core/             # Config, seguridad, dependencias
│   │   ├── db/               # Sesión y engine de la base de datos
│   │   ├── seed.py           # Usuario admin inicial
│   │   ├── seed_demo.py      # Datos de demo (18 meses, idempotente)
│   │   └── seed_e2e.py       # Datos deterministas para las pruebas e2e
│   ├── alembic/              # Migraciones versionadas
│   └── tests/                # pytest
├── frontend/                 # Next.js 16 + TypeScript + Tailwind
│   ├── src/app/              # App Router (vender, caja, inventario,
│   │                         #   historial, facturación, analítica)
│   ├── src/app/api/proxy/    # BFF: proxy server-side al backend
│   └── e2e/                  # Pruebas Playwright
└── docker-compose.yml        # PostgreSQL local
```

---

## Ejecutar localmente

**Requisitos:** Docker, Python 3.12, Node.js 20+.

```bash
# 1. Clonar
git clone https://github.com/dacq7/tendero.git
cd tendero

# 2. Base de datos (PostgreSQL en Docker, puerto 5436)
docker compose up -d

# 3. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # completar los secretos (ver abajo)
alembic upgrade head          # crear el esquema
python -m app.seed admin@tendero.co 'TuClave!' 'Admin'   # crear admin
python -m app.seed_demo       # (opcional) poblar datos de demo
uvicorn app.main:app --port 8020

# 4. Frontend (otra terminal)
cd frontend
npm install
cp .env.example .env.local    # set BACKEND_URL=http://localhost:8020
npm run dev -- --port 3001
```

El backend **no arranca sin sus secretos** (es a propósito — parte del hardening de seguridad). Genera cada uno con `openssl rand -hex 32` y colócalos en `backend/.env`:

```bash
# backend/.env
DATABASE_URL=postgresql://tendero:tendero@localhost:5436/tendero
JWT_SECRET=...
WOMPI_INTEGRITY_SECRET=...
WOMPI_EVENTS_SECRET=...
FISCAL_CUFE_SECRET=...
APP_ENV=development
```

### Ejecutar las pruebas

```bash
# Backend
cd backend && source .venv/bin/activate && pytest

# Frontend
cd frontend && npm test

# End-to-end (requiere Docker arriba)
cd frontend && npx playwright install chromium && npm run test:e2e
```

---

## Despliegue

El backend y PostgreSQL corren en **Railway**; el frontend en **Vercel**. La guía completa paso a paso está en [`DEPLOY.md`](DEPLOY.md), incluyendo la configuración de variables de entorno, el comando de arranque (migración + servidor) y los ajustes de CORS para producción.

---

<div align="center">

Construido por **Diego Correa** — [Veridis Dev](https://github.com/dacq7)

</div>
