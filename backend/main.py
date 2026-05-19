"""Onyx — AI coding assistant proxy backend.

OpenAI-compatible API that proxies requests to DeepSeek and logs all activity.
"""

import json
import logging
import secrets
from contextlib import asynccontextmanager
from typing import Optional

import traceback as _tb

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import async_session_factory, init_db

logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("onyx")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    log.info("Database tables initialised")
    yield


app = FastAPI(
    title="Onyx Proxy API",
    version="0.2.0",
    description="OpenAI-compatible proxy backend for Onyx CLI",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session


def _utcnow():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


async def validate_api_key(request: Request, db: AsyncSession):
    """Extract API key, validate against DB. Returns User or None (master key). Raises 401/403 on failure."""
    from .models import ApiKey, User
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    api_key = auth[7:]
    if not api_key:
        raise HTTPException(status_code=401, detail="Empty API key")

    # Master key bypass — for admin and registration
    if settings.api_key and api_key == settings.api_key:
        return None  # master key, no user tied

    # Look up API key in database (no join — simpler, more robust)
    result = await db.execute(
        select(ApiKey).where(ApiKey.key == api_key, ApiKey.active == 1)
    )
    apikey_obj = result.scalar_one_or_none()
    if apikey_obj is None:
        raise HTTPException(status_code=403, detail="Invalid API key")

    # Fetch the associated user
    user_result = await db.execute(select(User).where(User.id == apikey_obj.user_id))
    user = user_result.scalar_one()

    # Update last_used_at
    await db.execute(
        update(ApiKey).where(ApiKey.id == apikey_obj.id).values(last_used_at=_utcnow())
    )
    await db.commit()
    return user


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error("Unhandled exception: %s\n%s", exc, _tb.format_exc())
    return JSONResponse(status_code=500, content={"error": {"message": str(exc), "type": type(exc).__name__}})


@app.get("/health")
async def health():
    return {"status": "ok", "model": settings.deepseek_model}


@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": settings.public_models,
    }


@app.post("/v1/chat/completions")
async def chat_completions(
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    """OpenAI-compatible chat completions endpoint — proxies to DeepSeek."""
    from .models import ApiKey, User, Session as DBSession

    user = await validate_api_key(request, db)
    if user is None:
        raise HTTPException(status_code=403, detail="Master key cannot be used for chat")

    body = await request.json()

    messages = body.get("messages", [])
    model = body.get("model", settings.deepseek_model)
    stream = body.get("stream", True)
    session_id = body.get("session_id", None)

    # Resolve or create session for this user
    if session_id:
        result_s = await db.execute(
            select(DBSession).where(DBSession.id == session_id, DBSession.user_id == user.id)
        )
        session = result_s.scalar_one_or_none()
        if not session:
            session = DBSession(user_id=user.id, model=model)
            db.add(session)
            await db.commit()
            await db.refresh(session)
    else:
        session = DBSession(user_id=user.id, model=model)
        db.add(session)
        await db.commit()
        await db.refresh(session)

    resolved_session_id = str(session.id)

    from .proxy import proxy_chat

    generator = proxy_chat(
        db=db,
        user=user,
        messages=messages,
        model=model,
        session_id=resolved_session_id,
        stream=stream,
    )

    if not stream:
        result = await anext(generator)
        data = json.loads(result)
        return JSONResponse(content=data, headers={"X-Session-Id": resolved_session_id})

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Session-Id": resolved_session_id,
        },
    )


# ── Auth & Admin ──────────────────────────────────────────────


@app.post("/v1/auth/register")
async def register_key(
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    """Register a new API key. Requires master key."""
    from .models import ApiKey, User

    user = await validate_api_key(request, db)
    if user is not None:
        raise HTTPException(status_code=403, detail="Use the master key to register new keys")

    body = await request.json() if await request.body() else {}
    key_name = body.get("name", "")

    new_key = "onyx-" + secrets.token_urlsafe(32)
    new_user = User(name=key_name or f"user_{new_key[:8]}")
    db.add(new_user)
    await db.flush()

    apikey = ApiKey(key=new_key, user_id=new_user.id, name=key_name)
    db.add(apikey)
    await db.commit()
    await db.refresh(apikey)

    log.info("Registered new API key %s for user %s", apikey.id, new_user.id)
    return {
        "api_key": new_key,
        "key_id": apikey.id,
        "user_id": new_user.id,
        "name": key_name,
    }


@app.get("/admin/keys")
async def list_keys(
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    """List all API keys. Requires master key."""
    from .models import ApiKey, User

    user = await validate_api_key(request, db)
    if user is not None:
        raise HTTPException(status_code=403, detail="Admin only")

    result = await db.execute(
        select(ApiKey, User.name).join(User).order_by(ApiKey.created_at.desc())
    )
    keys = []
    for apikey, user_name in result:
        keys.append({
            "id": apikey.id,
            "key_prefix": apikey.key[:12] + "...",
            "user_id": apikey.user_id,
            "user_name": user_name,
            "active": bool(apikey.active),
            "created_at": apikey.created_at.isoformat() if apikey.created_at else None,
            "last_used_at": apikey.last_used_at.isoformat() if apikey.last_used_at else None,
        })
    return {"keys": keys, "total": len(keys)}


@app.delete("/admin/keys/{key_id}")
async def revoke_key(
    key_id: str,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    """Revoke an API key. Requires master key."""
    from .models import ApiKey

    user = await validate_api_key(request, db)
    if user is not None:
        raise HTTPException(status_code=403, detail="Admin only")

    result = await db.execute(select(ApiKey).where(ApiKey.id == key_id))
    apikey = result.scalar_one_or_none()
    if apikey is None:
        raise HTTPException(status_code=404, detail="Key not found")

    apikey.active = 0
    await db.commit()
    log.info("Revoked API key %s (user %s)", key_id, apikey.user_id)
    return {"status": "revoked", "key_id": key_id}
