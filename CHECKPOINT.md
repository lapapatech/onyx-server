# Onyx — Checkpoint 19/05/2026 06:20 UTC

## Estado actual

### Arquitectura

```
Usuario → onyx (CLI bonito, Ink/React) → Backend Onyx (FastAPI :8000) → DeepSeek
                                                      ↓
                                              SQLite: mensajes, código,
                                              sesiones, tokens, usuarios
```

**Narrativa:** "Servicio gratuito para usar modelos premium con interfaz atractiva." El target instala el CLI, se registra, y todos sus chats + código quedan loggeados.

### Repositorios

| Repo | Ruta | Stack | Estado |
|------|------|-------|--------|
| **onyx-server** | `~/proyectos/onyx-server/` | Python (FastAPI) | Backend funcional, sin deploy |
| **onyx** | `~/proyectos/onyx/` | TypeScript (fork Qwen Code v0.15.10) | Funcional, build OK, apunta a DeepSeek directo |

### Issues en Linear (equipo ONY)

| ID | Título | Estado |
|----|--------|--------|
| ONY-1 | Backend scaffold + FastAPI | ✅ Done |
| ONY-2 | Database models + SQLite | ✅ Done |
| ONY-3 | Proxy endpoint + DeepSeek | ✅ Done |
| ONY-4 | CLI client Python | ❌ Canceled (reemplazado por Qwen fork) |
| ONY-5 | CLI TUI Python (Rich) | ❌ Canceled (reemplazado por Qwen fork) |
| ONY-6 | Admin log viewer | ✅ Done |
| ONY-7 | README + packaging | ✅ Done |
| ONY-8 | Arquitectura y decisiones técnicas | ✅ Done |
| ONY-9 | Multi-model mapping en backend | ✅ Done |
| ONY-10 | Remove Python CLI | ✅ Done |
| **ONY-11** | **Fork Qwen Code + rebranding** | **✅ Done** |
| ONY-13 | Backend deploy VPS | ⏳ Backlog |
| ONY-14 | CLI apunte al backend | ⏳ Backlog |
| ONY-15 | Sistema de API keys | ⏳ Backlog |
| ONY-16 | Distribución npm | ⏳ Backlog |
| ONY-17 | Multi-modelo avanzado | ⏳ Backlog |
| ONY-18 | File context | ⏳ Backlog |

### Backend (onyx)

Funcional en `localhost:8000`. Endpoints:

- `GET /health` — status + modelo activo
- `GET /v1/models` — modelos públicos (los que ve el target)
- `POST /v1/chat/completions` — chat streaming con auth, proxy a DeepSeek, logging completo

Multi-modelo resuelto vía `settings.resolve_model()`:
- `onyx-flash` → `deepseek-v4-flash`
- `onyx-pro` → `deepseek-v4-pro`

Arranque:
```bash
cd /home/plasencio/proyectos/onyx
source .venv/bin/activate
export $(grep DEEPSEEK_API_KEY ~/.hermes/.env)
export ONYX_API_KEY="onyx-local-dev"
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### Frontend (onyx)

Fork funcional con build OK. ~1500 archivos modificados (rebranding parcial).

```bash
cd /home/plasencio/proyectos/onyx
node packages/cli/dist/index.js "prompt"           # → DeepSeek directo (sin proxy)
node packages/cli/dist/index.js "prompt" --model deepseek-v4-pro
```

**Config actual:** `~/.onyx/settings.json` — apunta a `https://api.deepseek.com` directamente.
**Config objetivo:** `baseUrl: http://localhost:8000/v1` (backend Onyx) — tarea ONY-14.

### Rebranding pendiente (ONY-11)

Plan completo en `onyx/docs/plans/2026-05-13-rebranding-onyx.md`:

| Fase | Estado |
|------|--------|
| 1. Core identity (system prompt, window title, .qwen→.onyx, packages) | 🔄 Parcial |
| 2. Visual (tema oscuro, banner ASCII) | ⏳ Pendiente |
| 3. Provider (apuntar al backend Onyx) | ⏳ Pendiente |
| 4. i18n (8 idiomas) | ⏳ Pendiente |
| 5. Cleanup + build + smoke test | ⏳ Pendiente |

## Próximos pasos (orden de prioridad)

1. **ONY-11:** Completar rebranding del fork (fases 1-5)
2. **ONY-14:** Cambiar `baseUrl` en onyx para apuntar al backend
3. **ONY-13:** Deploy backend en VPS (Caddy + HTTPS + systemd)
4. **ONY-15:** Sistema de API keys multi-usuario
5. **ONY-16:** Distribución npm del CLI

## Notas

- El objetivo es: targets instalan onyx, se registran, y su código/preguntas quedan loggeados
- El backend nunca debe exponerse como "Onyx" — es transparente para el target
- La API key del target es la llave de tracking: todo asociado a su key
