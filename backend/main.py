"""Onyx — AI coding assistant proxy backend.

OpenAI-compatible API that proxies requests to DeepSeek and logs all activity.
"""

import json
import logging
from contextlib import asynccontextmanager
from typing import Optional

import traceback as _tb

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
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
    version="0.1.0",
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


def validate_api_key(request: Request) -> str:
    """Extract and validate API key from Authorization header."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    api_key = auth[7:]
    if not api_key:
        raise HTTPException(status_code=401, detail="Empty API key")
    if api_key != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key


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
    api_key = validate_api_key(request)
    body = await request.json()

    messages = body.get("messages", [])
    model = body.get("model", settings.deepseek_model)
    stream = body.get("stream", True)
    session_id = body.get("session_id", None)

    from .models import User, Session as DBSession
    from sqlalchemy import select

    # Resolve user and session before streaming so we can return the session_id in headers
    result = await db.execute(select(User).where(User.api_key == api_key))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(api_key=api_key, name=f"user_{api_key[:8]}")
        db.add(user)
        await db.commit()
        await db.refresh(user)

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
        api_key=api_key,
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
