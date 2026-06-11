#!/usr/bin/env sh
# Arranque de PRODUCCIÓN del backend (Railway). Migra el esquema y luego sirve.
#
# - `set -e`: si la migración falla, NO se arranca el server (el deploy falla
#   ruidosamente en vez de servir contra un esquema desincronizado).
# - `${PORT:-8020}`: Railway inyecta $PORT; en local cae a 8020.
# - host 0.0.0.0: escucha en todas las interfaces del contenedor.
# - `exec`: uvicorn hereda el PID del proceso (señales/SIGTERM limpios).
# - sin recarga automática de código: esto es producción.
set -e

alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8020}"
