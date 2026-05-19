#!/usr/bin/env bash
# Onyx — arranque del backend
set -euo pipefail

cd "$(dirname "$0")"

# Cargar DeepSeek API key desde Hermes
export DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY:-$(grep DEEPSEEK_API_KEY ~/.hermes/.env | cut -d= -f2-)}"

# API key que los clientes usan para auth
export ONYX_API_KEY="${ONYX_API_KEY:-onyx-local-dev}"

# Puerto (default 8000)
PORT="${ONYX_PORT:-8000}"

echo "→ Onyx backend arrancando en 0.0.0.0:${PORT}"
echo "→ ONYX_API_KEY: ${ONYX_API_KEY:0:12}..."
echo "→ Model:        ${ONYX_MODEL:-onyx-flash}"
echo ""

source .venv/bin/activate
exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT}" --reload
