# Onyx — Proyecto Context

## ¿Qué es Onyx?

**Honeypot de AI coding assistant.** Se ofrece como "servicio gratuito para usar modelos premium", con interfaz atractiva (fork de Qwen Code). El usuario se registra, usa el CLI bonito, y por detrás todos sus chats, código, sesiones y consultas quedan registrados en el backend.

## Arquitectura

```
Usuario → onyx (CLI bonito, Ink/React) → Backend Onyx (FastAPI) → DeepSeek
                                                      ↓
                                              SQLite: mensajes, código,
                                              sesiones, tokens, usuarios
```

| Capa | Repo | Stack | Lo que ve el usuario |
|------|------|-------|---------------------|
| **Frontend (CLI)** | `~/proyectos/onyx/` | TypeScript, Ink (React), ESM | CLI premium tipo Codebuff, interfaz atractiva |
| **Backend (proxy)** | `~/proyectos/onyx-server/` | Python 3.11+, FastAPI, SQLite | API OpenAI-compatible (invisible para el usuario) |
| **Modelo real** | DeepSeek API | `deepseek-v4-flash` / `deepseek-v4-pro` | Nunca lo ve |

El backend expone modelos "premium" (`onyx-premium`, `onyx-flash`) que en realidad son DeepSeek. La API key del usuario es la llave de tracking: todo lo que envía queda asociado a su key.

## Público objetivo

Grupos pequeños. El operador pone el backend en su VPS, distribuye el CLI a los targets (npm, binario, o acceso directo). El target cree que está usando modelos caros gratis.

## Stack

- **Backend:** Python 3.11+, FastAPI, uvicorn, SQLAlchemy async, aiosqlite, httpx
- **Frontend:** TypeScript + Ink (React para terminal) — fork de Qwen Code v0.15.10
- **BD:** SQLite en `data/onyx.db`
- **Deploy:** Caddy (HTTPS) + systemd (pendiente ONY-13)

## Repositorios

| Repo | Ruta | Rol |
|------|------|-----|
| **onyx-server** (backend) | `~/proyectos/onyx-server/` | FastAPI proxy → DeepSeek. API OpenAI-compatible. Logging. |
| **onyx** (frontend) | `~/proyectos/onyx/` | CLI con TUI bonito (Ink/React). Fork de Qwen Code. |

**El CLI que ve el usuario es onyx.** El backend onyx-server es invisible.

## Estado actual

### Backend — ✅ Funcional

| Issue | Qué | Estado |
|-------|-----|--------|
| ONY-1 | Backend scaffold + FastAPI | ✅ Done |
| ONY-2 | Database models + SQLite | ✅ Done |
| ONY-3 | Proxy DeepSeek + streaming | ✅ Done |
| ONY-6 | Admin log viewer | ✅ Done |
| ONY-7 | README + packaging | ✅ Done |
| ONY-8 | Arquitectura y decisiones técnicas | ✅ Done |
| ONY-9 | Multi-model mapping (`resolve_model`) | ✅ Done |
| ONY-10 | Remove Python CLI | ✅ Done |

### Frontend (Qwen fork) — 🔄 ONY-11 en progreso

| Issue | Qué | Estado |
|-------|-----|--------|
| ONY-11 | Fork Qwen Code y rebranding completo | ✅ Done |

El fork está completamente rebrandeado y configurado para apuntar al backend Onyx en localhost:8000/v1.

### Pendiente (backlog)

| Issue | Qué | Prioridad |
|-------|-----|-----------|
| ONY-13 | Backend deploy VPS (Caddy + HTTPS) | ⬆ High |
| ONY-14 | CLI apunte al backend Onyx | ⬆ High |
| ONY-15 | Sistema de API keys multi-usuario | 🟡 Medium |
| ONY-16 | Distribución npm | 🟡 Medium |
| ONY-17 | Multi-modelo avanzado | ⬇ Low |
| ONY-18 | File context (--file flag) | ⬇ Low |

### Cancelado (reemplazado por Qwen fork)

| Issue | Qué | Motivo |
|-------|-----|--------|
| ONY-4 | CLI client Python | Qwen Code es mejor frontend |
| ONY-5 | CLI TUI Python (Rich) | Qwen Code tiene Ink/React nativo |

## Decisiones técnicas

- **Modelo por defecto: DeepSeek Flash** — barato ($0.14/M in). Pro solo si el target lo pide explícito.
- **Auth estática** — una sola variable `ONYX_API_KEY`. Auto-registro de usuarios en BD al primer uso.
- **Streaming** vía SSE (igual que OpenAI).
- **Auth estricta** — valida contra `ONYX_API_KEY`, no acepta cualquier token.
- **Multi-modelo** — el backend resuelve `onyx-flash` → `deepseek-v4-flash`, `onyx-pro` → `deepseek-v4-pro` vía `settings.resolve_model()`.

## Variables de entorno

| Variable | Descripción |
|----------|-------------|
| `DEEPSEEK_API_KEY` | API key de DeepSeek (desde `~/.hermes/.env`) |
| `ONYX_API_KEY` | API key del backend para los clientes |
| `ONYX_DATABASE_URL` | (opcional) Ruta SQLite, default `sqlite+aiosqlite:///data/onyx.db` |
| `ONYX_MODEL` | (opcional) Modelo por defecto, default `deepseek-chat` |
| `ONYX_DEBUG` | (opcional) Modo debug |

## Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/health` | GET | Health check, devuelve modelo activo |
| `/v1/models` | GET | Lista modelos públicos (los que ve el target) |
| `/v1/chat/completions` | POST | Chat streaming. Autentica, resuelve modelo, proxyea a DeepSeek, loggea todo |

## Arranque

```bash
cd /home/plasencio/proyectos/onyx-server
source .venv/bin/activate
export $(grep DEEPSEEK_API_KEY ~/.hermes/.env)
export ONYX_API_KEY="tu-clave"
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

## Admin

```bash
python admin/query_logs.py --stats      # Estadísticas de uso
python admin/query_logs.py --user X     # Mensajes de un usuario
python admin/query_logs.py --recent 20  # Últimos mensajes
```

## Notas

- Backend corriendo en localhost:8000
- Si hay errores de auth en ONYX_API_KEY, verificar env var
- Si hay problemas de importación, `pip install -e .` reinstala el paquete
- El fork de Qwen Code está en `~/proyectos/onyx/` (CLI) — ver su AGENTS.md
