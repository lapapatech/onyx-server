# Onyx — Checkpoint 19/05/2026 09:55 UTC

## Estado actual

### Arquitectura

```
Usuario → onyx CLI → https://onyx.devnullbox.net → CF Tunnel → :8000 → DeepSeek
                                                         ↓
                                                   SQLite logs
```

**Narrativa:** "Servicio gratuito para usar modelos premium con interfaz atractiva." El target instala el CLI, se registra, y todos sus chats + código quedan loggeados.

### Repositorios

| Repo | Ruta | Stack | Estado |
|------|------|-------|--------|
| **onyx** (CLI) | `~/proyectos/onyx/` | TypeScript (Ink) | Funcional, build OK, apunta a backend |
| **onyx-server** (backend) | `~/proyectos/onyx-server/` | Python (FastAPI) | Deployado VPS, systemd enabled |

### Producción

| Recurso | Valor |
|----------|-------|
| **URL** | `https://onyx.devnullbox.net` |
| **VPS** | `51.222.84.105` (hydra-node, Debian 12, debian) |
| **Puerto** | `127.0.0.1:8000` |
| **Systemd** | `onyx-server.service` (enabled, restart=always) |
| **Túnel CF** | Propio (dashboard), NO mezclado con kybalyon |
| **Master key** | En `/tmp/onyx_key.txt` (local) |
| **DB** | SQLite en `/home/debian/proyectos/onyx-server/data/onyx.db` |

### Issues en Linear (equipo ONY)

| ID | Título | Estado |
|----|--------|--------|
| ONY-11 | Fork Qwen Code + rebranding | ✅ Done |
| ONY-13 | Backend deploy VPS | ✅ Done |
| ONY-14 | CLI apunte al backend | ✅ Done |
| **ONY-15** | **Sistema de API keys multi-usuario** | **✅ Done** |
| ONY-16 | Distribución npm | ⏳ Backlog |
| ONY-17 | Multi-modelo avanzado | ⏳ Backlog |
| ONY-18 | File context | ⏳ Backlog |

### ONY-15 — ✅ COMPLETADO 19/05/2026

**Implementado y deployado:**
- Modelo `ApiKey` en BD (tabla separada de `users`, campo `active` para revocación)
- `POST /v1/auth/register` — registra key nueva (requiere master key)
- `GET /admin/keys` — lista todas las keys con estado
- `DELETE /admin/keys/{id}` — revoca una key (soft-delete, active=0)
- `validate_api_key()` — busca en BD por key + active=1, soporta master key bypass

**Bug resuelto:** La query original usaba `select(ApiKey, User).join(User)` que funcionaba de forma intermitente. Reemplazado por `select(ApiKey).where(ApiKey.key == api_key, ApiKey.active == 1)` + fetch separado de User. Código deployado en VPS y verificado con test end-to-end: registro → chat → revocación → denegación.

**Fix aplicado en:** `backend/main.py:77-94` — local + VPS (sin commit aún).

### Endpoints actuales

| Endpoint | Auth | Descripción |
|----------|------|-------------|
| `GET /health` | Ninguna | Health check |
| `GET /v1/models` | Ninguna | Modelos públicos |
| `POST /v1/chat/completions` | API key (user) | Proxy chat → DeepSeek |
| `POST /v1/auth/register` | Master key | Registrar nueva API key |
| `GET /admin/keys` | Master key | Listar keys |
| `DELETE /admin/keys/{id}` | Master key | Revocar key |

### Comandos SSH VPS

```bash
sshpass -p 'Nodata7814!' ssh debian@51.222.84.105

# Estado servicio
sudo systemctl status onyx-server
sudo journalctl -u onyx-server -f

# Reiniciar tras cambios
sudo systemctl restart onyx-server

# DB directa
cd ~/proyectos/onyx-server
.venv/bin/python3 -c "import sqlite3; db=sqlite3.connect('data/onyx.db'); ..."
```

### Archivos modificados en ONY-15

```
onyx-server/backend/models.py   — ApiKey model, User sin api_key
onyx-server/backend/main.py     — validate_api_key refactor + register + admin
onyx-server/backend/proxy.py    — proxy_chat acepta User, no api_key
```

Sin commits locales desde los cambios de ONY-15.
