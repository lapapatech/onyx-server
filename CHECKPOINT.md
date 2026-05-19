# Onyx — Checkpoint 19/05/2026 12:00 UTC (FINAL MVP)

## Estado: MVP COMPLETO ✅

El honeypot funciona de punta a punta: CLI → backend → DeepSeek con logging completo.

### Arquitectura

```
Usuario → onyx CLI → https://onyx.devnullbox.net → CF Tunnel → :8000 → DeepSeek
                                                         ↓
                                                   SQLite logs
```

**Narrativa:** "Startup con funding — modelos premium gratis durante beta." El target instala el CLI, se registra, y todos sus chats + código quedan loggeados.

### Repositorios

| Repo | Ruta | Stack | Estado |
|------|------|-------|--------|
| **onyx** (CLI) | `~/proyectos/onyx/` | TypeScript (Ink) | Build OK, README startup narrative, 0 refs Qwen |
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

### Issues — TODOS COMPLETADOS ✅

| ID | Título | Estado |
|----|--------|--------|
| ONY-11 | Fork Qwen Code + rebranding | ✅ Done |
| ONY-13 | Backend deploy VPS | ✅ Done |
| ONY-14 | CLI apunte al backend | ✅ Done |
| ONY-15 | Sistema de API keys multi-usuario | ✅ Done |
| ONY-16 | Distribución npm | ✅ Done |
| ONY-17 | Multi-modelo avanzado | ✅ Done |
| ONY-18 | File context (cubierto por @file del fork) | ✅ Done |

### Catálogo de modelos públicos

| Modelo | Resuelve a | Personalidad |
|--------|-----------|-------------|
| `onyx-flash` | `deepseek-v4-flash` | Rápido, diario |
| `onyx-sonnet` | `deepseek-v4-flash` | Balanceado |
| `onyx-pro` | `deepseek-v4-pro` | Razonamiento profundo |
| `onyx-opus` | `deepseek-v4-pro` | Máxima potencia |

### Endpoints

| Endpoint | Auth | Descripción |
|----------|------|-------------|
| `GET /health` | Ninguna | Health check |
| `GET /v1/models` | Ninguna | 4 modelos públicos |
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

### npm package

```bash
# Build + publish
cd ~/proyectos/onyx
npm run bundle && npm run prepare:package
cd dist && npm publish
```

### Commits hoy (onyx-server)

```
f01f4d6 docs: mark ONY-17 complete in checkpoint
9ad9e72 feat(onyx-server): multi-model support — onyx-flash + onyx-pro (ONY-17)
1dbbf76 docs: mark ONY-16 complete in checkpoint
9ea6a1b feat(onyx-server): multi-user API key system (ONY-15)
```

### Commits hoy (onyx)

```
827f2ce fix: remove Qwen references from web-template source files
58de054 fix: remove Alibaba Group from system prompt
1c1f427 feat(cli): npm distribution prep — v0.1.0, Onyx README, keywords (ONY-16)
```

### Recursos de target para testing

| Key | ID | User |
|-----|----|------|
| `onyx-aSX5PKMO-9zLFelD98NPK5o-jW_k_gVDpAPo7hTdg8Q` | e6f7150264c2 | demo-machine |
