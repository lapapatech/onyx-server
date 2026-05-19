# Onyx — Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a distribution-ready AI coding assistant CLI that promises "free premium models" but actually routes through our backend proxy (DeepSeek) and logs all user activity.

**Architecture:** Two-component system: a FastAPI backend proxy (OpenAI-compatible API) that intercepts every LLM call, logs it to SQLite, and forwards to DeepSeek; and a Python CLI client that users install, configured to point at our backend. Admin panel via CLI scripts to query logs.

**Tech Stack:** Python 3.11+, FastAPI, uvicorn, SQLite, httpx, rich (CLI), typer (CLI), DeepSeek API

---

## Project Structure

```
/home/plasencio/proyectos/onyx/
├── backend/
│   ├── main.py              # FastAPI app + endpoints
│   ├── models.py            # SQLite models (users, sessions, messages)
│   ├── database.py          # DB setup + helpers
│   ├── proxy.py             # DeepSeek proxy logic
│   ├── config.py            # Configuration
│   └── requirements.txt
├── cli/
│   ├── onyx.py              # Entry point (typer CLI)
│   ├── client.py            # HTTP client to backend
│   ├── tui.py               # Terminal UI (rich)
│   ├── config.py            # Local config management
│   └── requirements.txt
├── admin/
│   └── query_logs.py        # Scripts to browse logs
├── docs/
│   └── plan/
│       └── README.md        # This file
└── README.md                # Project README
```

---

### Task 1: Project scaffold + backend skeleton

**Objective:** Create project directory, virtual env, and basic FastAPI server that responds to health checks.

**Files:**
- Create: `backend/main.py`
- Create: `backend/config.py`
- Create: `backend/requirements.txt`
- Create: `backend/__init__.py`

### Task 2: Database models

**Objective:** Define SQLite schema for users, sessions, messages. Auto-create tables on startup.

**Files:**
- Create: `backend/database.py`
- Create: `backend/models.py`

### Task 3: Proxy endpoint + DeepSeek integration

**Objective:** Implement `/v1/chat/completions` endpoint that accepts OpenAI-format requests, logs them, proxies to DeepSeek, logs response, returns streaming.

**Files:**
- Modify: `backend/main.py`
- Create: `backend/proxy.py`

### Task 4: CLI client — config + API client

**Objective:** CLI client with config management (server URL, API key) and HTTP client that talks to our backend in OpenAI format.

**Files:**
- Create: `cli/onyx.py`
- Create: `cli/client.py`
- Create: `cli/config.py`
- Create: `cli/requirements.txt`

### Task 5: CLI TUI — interactive chat

**Objective:** Terminal UI with rich: chat interface, streaming responses, markdown rendering, file context.

**Files:**
- Create: `cli/tui.py`
- Modify: `cli/onyx.py`

### Task 6: Admin log viewer

**Objective:** CLI scripts to browse logged data — list users, view sessions, search prompts.

**Files:**
- Create: `admin/query_logs.py`

### Task 7: README + packaging

**Objective:** Write project README (public-facing with value prop), package CLI for pip install.

**Files:**
- Create: `cli/setup.py`
- Create: `README.md`
- Modify: `cli/requirements.txt`

---

## Execution Order

Tasks 1 → 2 → 3 (backend first, testable independently)
Tasks 4 → 5 (CLI client)
Task 6 (admin panel — can overlap with CLI)
Task 7 (documentation + packaging)

---

## Verification

After each task:
- Backend: `curl http://localhost:8000/health` returns OK
- Backend: `curl -X POST http://localhost:8000/v1/chat/completions` with test payload returns streaming
- CLI: `onyx chat "hello"` streams response
- Admin: `python3 admin/query_logs.py --recent` shows logged messages
- Packaging: `pip install ./cli` works
