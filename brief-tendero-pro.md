# Brief de arranque — Tendero (versión profesional, nivel Veridis)

Pega este documento al inicio de un chat nuevo (o úsalo como guion con Claude Code).
Es el reemplazo del demo anterior: aquí el objetivo es **software vendible**, no una prueba de concepto.

> Nombre de trabajo: **Tendero** (por Veridis Dev). Considera renombrarlo a algo más
> brandeable si va a portafolio comercial.
>
> **Lleva contigo el archivo `SKILL_FRONTEND.md`** (lo tienes del proyecto anterior) y ponlo en
> la raíz del proyecto nuevo: la dirección de diseño profesional depende de él.

---

## 0. Cómo leer este documento

Esto NO es un build de unas horas. Es un **producto por fases**, multi-sesión. Cada fase se
construye con su propio `/feature`, se prueba, se commitea y se cierra antes de pasar a la
siguiente. Intentar todo de una vez produce un demo, no un producto. El orden de fases está en
la sección 9.

## 1. Qué construir y para quién

Un **SaaS de punto de venta + gestión de inventario + facturación + analítica** para **tiendas
de barrio y pequeños comercios en Colombia**. Es un vertical comercial de Veridis Dev: debe poder
venderse y operar en un negocio real.

- Idioma: español (es-CO).
- Usuarios: **administrador** (dueño) y **cajero** (operador de mostrador) — roles distintos.
- Calidad: producto, no demo. Arquitectura en capas, migraciones, auth real, pruebas serias,
  manejo de dinero sin errores, integraciones externas reales (sandbox).

## 2. Qué lo hace profesional (vs. el demo anterior)

El demo tenía: SQLite, sin auth, stock como un número, venta = registro, "factura" = recibo,
métricas del día. La versión profesional exige:

- **Inventario serio**: precio de costo y de venta (márgenes), proveedores, movimientos de
  inventario auditables (entrada/salida/ajuste/merma), unidades, IVA por producto, código de
  barras, kardex por producto.
- **Cada venta genera una factura** con numeración secuencial propia, impuestos, y un **estado
  de emisión fiscal** (pendiente/aceptada/rechazada + CUFE) cuando se integra la facturación DIAN.
- **Pagos reales con Wompi** (sandbox primero): el cobro no es un botón falso, es una transacción.
- **Analítica de verdad**: el admin filtra métricas por día / semana / mes / año / rango, con
  ventas, ticket promedio, márgenes, productos top, horas pico, rotación de inventario.
- **Caja**: apertura y cierre de caja con arqueo (feature estándar de un POS serio).
- **Auth y roles**: login real, permisos por rol, auditoría de quién hizo qué.

## 3. Stack (fijo)

- Frontend: **Next.js (App Router) + TypeScript + Tailwind CSS**. Primitivas accesibles
  (Radix/shadcn permitido como base), pero el lenguaje visual es propio (ver SKILL_FRONTEND.md).
- Backend: **Python + FastAPI** con arquitectura en capas (routers → services → repositories →
  models/schemas). **SQLModel/SQLAlchemy**.
- Base de datos: **PostgreSQL** (local vía Docker `docker-compose`), con **Alembic** para
  migraciones desde el día uno. Nada de SQLite aquí.
- Auth: **JWT** (access + refresh) o sesión server-side; hashing de contraseñas con `bcrypt`/`argon2`.
- Pagos: **Wompi** (Widget o API; sandbox primero; webhooks; firma de integridad; llave privada
  solo en servidor).
- Facturación electrónica: **integración con un Proveedor Tecnológico autorizado por la DIAN**
  vía API REST (mock en local, sandbox del proveedor para pruebas). Ver sección 7.
- Pruebas: **pytest** (backend, cobertura alta en dinero/inventario/facturación), **Vitest**
  (componentes) y **Playwright** (e2e del flujo de venta).
- Deploy (fase final, no al inicio): frontend en **Vercel**, backend + Postgres en **Railway**.

## 4. Decisiones de arquitectura (inmutables)

- Monorepo `frontend/` + `backend/`, un repo, historial git limpio con commits convencionales.
- **Toda** la lógica de negocio vive en el backend, en la capa de servicios. El cliente orquesta.
- El dinero se maneja en **enteros (centavos o pesos enteros COP)**, nunca float.
- Migraciones versionadas con Alembic; el esquema nunca se toca a mano en producción.
- Integraciones externas (Wompi, PT de facturación) detrás de **interfaces/adaptadores**, con
  una implementación **mock** para local/test y una **real** para sandbox/producción, conmutable
  por variable de entorno. Así se construye y prueba sin llaves reales y se cambia sin reescribir.
- Idempotencia en operaciones de pago y emisión de factura (evitar cobros/facturas duplicadas).
- Auditoría: tablas de movimientos y log de acciones sensibles (quién, qué, cuándo).

## 5. Modelo de dominio (entidades serias)

- **User** (rol: admin/cajero), con auth y auditoría.
- **Product**: nombre, SKU, código de barras, categoría, proveedor, **precio_costo**,
  **precio_venta**, IVA (%), unidad, stock, stock_minimo, activo.
- **Supplier** (proveedor): datos de contacto, productos asociados.
- **InventoryMovement**: tipo (entrada/salida/ajuste/merma), producto, cantidad, costo unitario,
  motivo, usuario, timestamp — kardex completo, no un número suelto.
- **Customer** (opcional por venta): tipo y número de documento (CC/NIT), para la factura.
- **Sale** + **SaleItem**: con snapshot de precio y de IVA por línea.
- **Invoice**: numeración secuencial propia, subtotales, IVA, total, método de pago,
  referencia de transacción Wompi, **estado DIAN** (none/pending/accepted/rejected) y CUFE.
- **Payment**: transacción Wompi vinculada a la venta (estado, referencia, método).
- **CashRegisterSession**: apertura/cierre de caja, monto inicial, ventas, arqueo, diferencias.

## 6. Módulos / épicas

1. **Auth y usuarios**: login, roles (admin/cajero), permisos, recuperación básica.
2. **Inventario**: productos, proveedores, movimientos (kardex), costos/márgenes, alertas de
   stock bajo, entradas de mercancía.
3. **Ventas + Caja**: pantalla de venta (protagonista), carrito, cobro, apertura/cierre de caja.
4. **Pagos (Wompi)**: cobro real por Wompi en sandbox, confirmación por webhook, conciliación.
5. **Facturación**: factura interna por cada venta + integración con PT de la DIAN (sección 7).
6. **Analítica**: dashboard con filtros temporales (día/semana/mes/año/rango) y métricas reales.
7. **Historial**: facturas y ventas con búsqueda y filtros, detalle, reimpresión/descarga.

## 7. Integraciones externas (la parte que define si es serio)

### 7.1 Wompi (pagos)

- Dos modos posibles: **Widget/Web Checkout** (más rápido de integrar) o **API** (más control).
  Empieza por el que el `architect` recomiende según el flujo de mostrador; documenta la elección.
- **Sandbox primero**: usar las llaves de prueba (pública y privada). La **llave privada vive
  solo en el servidor**, nunca en el cliente ni en el repo.
- Métodos relevantes en Colombia: tarjeta, PSE, Nequi, Daviplata, Bancolombia (BNPL), efectivo
  en corresponsales, Puntos Colombia. Empezar con tarjeta + PSE + Nequi.
- **Firma de integridad** en cada transacción (calculada en el servidor).
- **Webhook**: endpoint en el backend que recibe el evento de Wompi y actualiza el estado del
  pago/venta de forma idempotente. La venta no se da por pagada hasta la confirmación.
- Moneda siempre COP. Montos en centavos.
- Documentación: docs.wompi.co / wompi.com/es/co/desarrolladores.

### 7.2 Facturación electrónica DIAN (vía Proveedor Tecnológico)

**Realidad regulatoria (no inventar validez fiscal):**
- Una factura electrónica con validez fiscal **no** es un PDF generado por la app. Requiere
  habilitación ante la DIAN (Resolución 165 de 2023) y, en la práctica para una casa de
  software, **integrarse con un Proveedor Tecnológico (PT) autorizado** (hay 80+: Alanube,
  Factus, MATIAS API, etc.) que transmite a la DIAN y devuelve estado + CUFE.
- El comercio necesita su **RUT con Responsabilidad 52** y una **resolución de numeración**
  autorizada. Eso es del cliente, no del software, pero el producto debe soportarlo
  (configuración de resolución y rangos de numeración).

**Cómo lo construye la app (arquitectura, no compliance):**
- La app **siempre** crea su factura interna con numeración secuencial al cerrar cada venta.
- La **emisión fiscal** es una capa de integración detrás de una interfaz `FiscalProvider`:
  - **MockFiscalProvider** para local/test: simula aceptación/rechazo, genera un CUFE falso,
    permite construir y probar todo el flujo sin cuenta real.
  - **RealFiscalProvider** para sandbox/producción: mapea la factura al modelo del PT elegido,
    envía por API REST, guarda estado (pending→accepted/rejected) y CUFE.
  - Conmutable por env var (`FISCAL_PROVIDER=mock|real`).
- Estado DIAN visible en la factura y en el historial. Reintentos idempotentes ante fallo.

> No prometas validez fiscal en el demo/portafolio: deja claro que la emisión real exige la
> habilitación del comercio ante la DIAN y un PT autorizado. El software está *listo para
> integrarse*; la habilitación es del negocio.

## 8. Analítica de datos (de verdad)

- Endpoints de agregación en el backend (no cálculos en el cliente), parametrizados por rango
  de fechas y granularidad (día/semana/mes/año).
- Métricas: ventas totales y por periodo, número de transacciones, **ticket promedio**,
  **márgenes** (gracias a precio_costo), productos y categorías top, horas/días pico,
  **rotación de inventario** y stock valorizado, ventas por método de pago, por cajero.
- Series temporales para gráficas (líneas/barras) y comparativas periodo vs periodo anterior.
- Considerar vistas materializadas o consultas indexadas si el volumen lo amerita.
- Frontend: dashboard con selector de rango y granularidad, gráficas reales (recharts u similar),
  exportación a CSV.

## 9. Cómo construirlo — por fases (cada una con su /feature)

Construir en este orden, una fase por sesión de `/feature`, probando y commiteando entre cada una:

- **Fase 0 — Cimientos**: monorepo, Docker Postgres, Alembic, FastAPI en capas, Next + diseño
  base (SKILL_FRONTEND.md), auth con roles, CI local (pytest + Vitest). Sin features de negocio aún.
- **Fase 1 — Inventario**: productos, proveedores, movimientos (kardex), costos/márgenes,
  alertas, entradas. Con migraciones y pruebas.
- **Fase 2 — Ventas + Caja + Factura interna**: pantalla de venta, carrito, cobro (aún sin
  Wompi real), apertura/cierre de caja, y factura interna con numeración por cada venta.
- **Fase 3 — Pagos Wompi (sandbox)**: cobro real por Wompi, webhook idempotente, conciliación.
- **Fase 4 — Facturación DIAN (mock → sandbox PT)**: interfaz FiscalProvider, mock local,
  integración con el PT en sandbox, estado + CUFE en factura e historial.
- **Fase 5 — Analítica**: endpoints de agregación con filtros temporales y dashboard real.
- **Fase 6 — Pulido + deploy**: e2e con Playwright, hardening de seguridad, deploy Vercel/Railway.

Para cada fase, el flujo es el de siempre: `/feature` con el alcance de la fase → el architect
planea → se construye en modo autónomo (acceptEdits + allow/deny) → hooks formatean → test-gate
exige tests → security-reviewer audita → revisar en vivo → commits convencionales.

## 10. Entorno local

- **Postgres por Docker** (`docker-compose.yml` en la raíz). Elegir un puerto que NO choque con
  los contenedores ya existentes en la máquina (evitar 5432/5434/5435 si están ocupados; usar
  p. ej. **5436**). Documentar el puerto elegido.
- **Backend** en `backend/` con venv; Alembic para migrar; FastAPI en un puerto libre
  (evitar 8000/8001; usar p. ej. **8010**).
- **Frontend** en `frontend/`; `npm run dev` (probablemente **:3001**).
- **Variables de entorno** (en `.env.local` / `.env`, nunca en el repo; incluir `.env.example`):
  `DATABASE_URL`, `JWT_SECRET`, `WOMPI_PUBLIC_KEY`, `WOMPI_PRIVATE_KEY` (sandbox),
  `WOMPI_EVENTS_SECRET`, `FISCAL_PROVIDER`, llaves del PT (sandbox), `NEXT_PUBLIC_API_URL`.
- CORS del backend acotado al origen del frontend.

## 11. Cómo probar

- **Backend (pytest)**: lógica de venta atómica, kardex/movimientos, cálculo de IVA y márgenes,
  numeración de facturas, idempotencia de pagos y de emisión fiscal, agregaciones de analítica,
  permisos por rol. Cobertura alta en todo lo que toca dinero o stock.
- **Frontend (Vitest)**: componentes clave (carrito, venta, filtros de analítica, formularios).
- **E2E (Playwright)**: flujo completo de venta cobrando en Wompi sandbox y generando factura
  (con FiscalProvider en mock o sandbox).
- **Sandboxes**: Wompi sandbox para pagos; sandbox del PT para facturación. Documentar cómo
  obtener y configurar las llaves de prueba.

## 12. Definition of Done (profesional)

- [ ] Auth con roles funcionando; permisos efectivos por rol; acciones sensibles auditadas.
- [ ] Inventario con kardex auditable, costos/márgenes y alertas; migraciones Alembic limpias.
- [ ] Venta atómica → factura interna con numeración secuencial; caja con apertura/cierre/arqueo.
- [ ] Cobro real por Wompi en sandbox confirmado por webhook idempotente.
- [ ] Emisión fiscal vía FiscalProvider: mock en local y sandbox del PT con estado + CUFE.
- [ ] Analítica con filtros día/semana/mes/año/rango y métricas reales (incl. márgenes).
- [ ] Pruebas pytest + Vitest verdes; e2e del flujo de venta verde.
- [ ] Sin secretos en código ni logs; `.env.example` presente; llaves solo en entorno.
- [ ] Corre end-to-end en local con Docker Postgres; documentado en README.
- [ ] security-reviewer sin hallazgos críticos ni altos.
- [ ] Deploy documentado (y, en Fase 6, desplegado).

## 13. Reglas de oro y seguridad

- Secretos solo en variables de entorno; nunca en repo ni logs. `.env.example` con placeholders.
- Llave privada de Wompi y llaves del PT **solo en el servidor**. Validar firma de webhooks.
- Manejar datos personales conforme a la **Ley 1581 de 2012 (Habeas Data)**: minimizar, proteger,
  no exponer documentos de clientes sin necesidad.
- Idempotencia en pagos y emisión de facturas. Dinero en enteros, nunca float.
- Tests por feature; nada "hecho" sin su test. Commits convencionales. Nada a producción sin DoD.

## 14. Diseño (frontend-design skill)

Incluir `SKILL_FRONTEND.md` en la raíz y leerlo antes de diseñar. Dirección profesional:

- La pantalla **Vender** es la protagonista: rápida, legible a un brazo de distancia, objetivos
  de toque grandes; pensada para uso real en mostrador (tablet/desktop).
- El **dashboard de analítica** es la segunda cara: serio, denso pero claro, con jerarquía de
  datos real (no tarjetas vacías ni gradientes decorativos).
- Tipografía con intención (display + body + una mono para cifras/precios tabulares).
- Estados vacíos y de error que guían, no que decoran. Accesibilidad de base (focus visible,
  responsive, motion reducido respetado).
- Gastar la audacia en un elemento memorable (p. ej. el ticket de cobro), y mantener el resto
  disciplinado.
