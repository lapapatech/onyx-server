# Onyx — Checkpoint 20/05/2026 18:37 UTC (YOLO sesión 2)

## Estado: MVP EXTENDIDO ✅

Todos los issues ONY-11 a ONY-23 completados.

### Nuevos issues (esta sesión)

| ID | Título | Estado |
|----|--------|--------|
| ONY-19 | Dashboard web de logs | ✅ Done |
| ONY-20 | Rate limiting por API key | ✅ Done |
| ONY-21 | Notificación Telegram | ✅ Done |
| ONY-22 | Instalador one-liner | ✅ Done |
| ONY-23 | Rotación de modelos falsos | ✅ Done |

### Producción

| Recurso | Valor |
|----------|-------|
| **URL** | `https://onyx.devnullbox.net` |
| **VPS** | `51.222.84.105` (hydra-node, Debian 12, debian) |
| **Health** | 🟢 200 — deepseek-v4-flash |
| **Dashboard** | 🟢 `/admin/dashboard` |
| **Chat** | 🟢 200 — rate limit 60/min |
| **Telegram** | 🟢 @onyx_monitor_bot — alertas de actividad |
| **Installer** | 🟢 `curl -sSL https://onyx.devnullbox.net/install.sh \| bash` |
| **Model rotation** | 🟢 6 temas, rota cada 24h (`ONYX_ROTATION_INTERVAL`) |

### Archivos nuevos

- `backend/dashboard.py` — HTML vanilla + 4 endpoints JSON
- `backend/rate_limit.py` — sliding window counter, 429 con Retry-After
- `backend/notifier.py` — Telegram alerts (fire & forget)
- `backend/install.sh` — One-liner installer (servido como GET /install.sh)
- `backend/model_rotator.py` — Rotación periódica de catálogo de modelos

### Archivos modificados

- `backend/config.py` — model_map y public_models delegando al rotator
- `backend/main.py` — integración dashboard, rate limit, notifier, endpoint install.sh

### Telegram notifier

- Bot: @onyx_monitor_bot (token: 8308867002:AAH...)
- Chat ID: 8517465061 (personal DM)
- Env vars en drop-in systemd: `/etc/systemd/system/onyx-server.service.d/env.conf`
- Dispara en: nuevo target (primera sesión) o target inactivo >24h

### Model rotation

- 6 temas: constellations, elements, mythical, minerals, celestial, neuro
- 4-6 modelos por rotación, 70% flash / 30% pro
- Intervalo: 24h (configurable con `ONYX_ROTATION_INTERVAL`)
- `_backend` oculto en `/v1/models`

### Comandos SSH VPS

```bash
sshpass -p 'Nodata7814!' ssh debian@51.222.84.105

# Estado servicio
sudo systemctl status onyx-server
sudo journalctl -u onyx-server -f

# Reiniciar tras cambios
sudo systemctl restart onyx-server

# Logs del notifier
sudo journalctl -u onyx-server | grep notif
```
