# Tendero

SaaS de punto de venta, inventario, facturación y analítica para tiendas de
barrio y pequeños comercios en Colombia (es-CO). Vertical comercial de Veridis Dev.

## Estado
Construcción por fases (ver `brief-tendero-pro.md`).
- [ ] **Fase 0 — Cimientos** (en curso)
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
- Frontend: Next.js (App Router) + TypeScript + Tailwind
- Backend: Python + FastAPI en capas (routers → services → repositories → models/schemas), SQLModel/SQLAlchemy
- DB: PostgreSQL (Docker) + Alembic
- Auth: JWT (access + refresh), hashing argon2/bcrypt

## Arranque local
Pendiente de documentar al cerrar Fase 0.

## Reglas
- Secretos solo en `.env` (nunca en el repo). Ver `.env.example`.
- Dinero en enteros (centavos COP), nunca float.
- Migraciones siempre con Alembic.
