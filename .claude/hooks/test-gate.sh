#!/usr/bin/env bash
# PreToolUse (matcher: Bash). Bloquea `git commit` si los tests FALLAN.
# pytest exit codes: 0 = todos pasaron, 1 = fallos, 5 = no se recogieron tests.
# Bloquea solo en 1 (fallo real). 0 y 5 (sin tests aún) pasan.

input="$(cat)"
cmd="$(printf '%s' "$input" | jq -r '.tool_input.command // empty')"

case "$cmd" in
  *"git commit"*)
    ROOT="$HOME/Projects/tendero"

    # ── Backend (pytest) ──
    PYTEST="$ROOT/backend/.venv/bin/pytest"
    if [ -x "$PYTEST" ]; then
      ( cd "$ROOT/backend" && "$PYTEST" -q > /tmp/tendero-pytest.log 2>&1 )
      code=$?
      if [ "$code" -eq 1 ]; then
        echo "Tests del backend fallaron — commit bloqueado. Revisa /tmp/tendero-pytest.log" >&2
        exit 2
      fi
    fi

    # ── Frontend (vitest), solo si hay script de test configurado ──
    if [ -f "$ROOT/frontend/package.json" ] && grep -q '"test"' "$ROOT/frontend/package.json"; then
      ( cd "$ROOT/frontend" && npm test --silent > /tmp/tendero-vitest.log 2>&1 )
      fcode=$?
      if [ "$fcode" -ne 0 ]; then
        echo "Tests del frontend fallaron — commit bloqueado. Revisa /tmp/tendero-vitest.log" >&2
        exit 2
      fi
    fi
    ;;
esac
exit 0
