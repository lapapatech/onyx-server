# Onyx

Backend proxy para AI coding assistant — API OpenAI-compatible que enruta a DeepSeek y loggea toda la actividad.

**El CLI que usa el target NO está en este repo.** Está en `~/proyectos/onyx/` (fork de Qwen Code).

## Arquitectura

```
onyx (CLI bonito) ──HTTP──► Backend Onyx (este repo) ──HTTP──► DeepSeek API
                                      │
                                      ▼
                                   SQLite (logs)
```

- Backend expone API OpenAI-compatible (invisible para el target)
- Proxy a DeepSeek con resolución de modelos (`onyx-flash` → `deepseek-v4-flash`, `onyx-pro` → `deepseek-v4-pro`)
- Todos los mensajes, tokens, usuarios y sesiones loggeados a SQLite
- Auth por API key
- Streaming SSE

## Quick Start (backend)

```bash
cd /home/plasencio/proyectos/onyx-server
source .venv/bin/activate
export $(grep DEEPSEEK_API_KEY ~/.hermes/.env)
export ONYX_API_KEY="tu-clave-secreta"
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

## Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/health` | GET | Health check, devuelve modelo activo |
| `/v1/models` | GET | Modelos públicos (los que ve el target) |
| `/v1/chat/completions` | POST | Chat streaming con auth + proxy + logging |

## Admin

```bash
cd /home/plasencio/proyectos/onyx-server
source .venv/bin/activate
python admin/query_logs.py --stats
python admin/query_logs.py --recent 20
python admin/query_logs.py --user <id>
python admin/query_logs.py --search "error"
```
