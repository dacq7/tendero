#!/usr/bin/env sh
# Arranque del backend: migra el esquema y luego sirve. Atajo para correr el flujo
# de producción EN LOCAL (`sh start.sh`).
#
# NOTA: en Railway el comando de arranque NO es este script. Railway usa el builder
# Railpack, que construye una imagen con copiado SELECTIVO de archivos: un script
# suelto como este puede no quedar en la imagen de runtime (de ahí el error
# "cannot open start.sh"). Por eso el arranque productivo va INLINE en
# `railway.json` (deploy.startCommand) y depende solo de binarios en PATH
# (alembic, uvicorn) + el código de la app. Mantén ambos en sincronía.
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
