#!/usr/bin/env bash
# PostToolUse (matcher: Write|Edit). Formatea el archivo recién escrito.
# No bloquea nada: solo deja el código limpio sin que tengas que pedirlo.

input="$(cat)"
f="$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')"
[ -z "$f" ] && exit 0

ROOT="$HOME/Projects/tendero"
RUFF="$ROOT/backend/.venv/bin/ruff"

case "$f" in
  *.py)
    if [ -x "$RUFF" ]; then
      "$RUFF" format "$f" >/dev/null 2>&1
      "$RUFF" check --fix "$f" >/dev/null 2>&1
    fi
    ;;
  *.ts|*.tsx|*.jsx|*.js)
    ( cd "$ROOT/frontend" && npx -y eslint --fix "$f" >/dev/null 2>&1 )
    ;;
esac

exit 0
