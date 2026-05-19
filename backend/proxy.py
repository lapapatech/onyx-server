"""DeepSeek proxy logic — forward + log + stream."""

import json
import logging
import time
from typing import AsyncGenerator, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .models import Message, Session, User

log = logging.getLogger("onyx.proxy")

DEEPSEEK_CHAT_URL = f"{settings.deepseek_base_url}/v1/chat/completions"


async def _resolve_user(db: AsyncSession, api_key: str) -> User:
    """Find or create user by API key."""
    result = await db.execute(select(User).where(User.api_key == api_key))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(api_key=api_key, name=f"user_{api_key[:8]}")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        log.info("Created new user %s", user.id)
    return user


async def _resolve_session(
    db: AsyncSession, user: User, session_id: Optional[str], model: str
) -> Session:
    """Find existing session or create new one."""
    if session_id:
        result = await db.execute(
            select(Session).where(Session.id == session_id, Session.user_id == user.id)
        )
        session = result.scalar_one_or_none()
        if session:
            return session
    session = Session(user_id=user.id, model=model)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


def _extract_text(content) -> str:
    """Extract plain text from OpenAI content field (string or list)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
        return "\n".join(parts) if parts else str(content)
    return str(content)


async def proxy_chat(
    db: AsyncSession,
    api_key: str,
    messages: list,
    model: str,
    session_id: Optional[str] = None,
    stream: bool = True,
) -> AsyncGenerator[str, None]:
    """Proxy chat completion request to DeepSeek, log it, stream response."""
    # Resolve user and session
    user = await _resolve_user(db, api_key)
    session = await _resolve_session(db, user, session_id, model)
    session_id = session.id  # use resolved id

    # Log user messages
    for msg in messages:
        if msg.get("role") in ("user", "system"):
            db_msg = Message(
                session_id=session_id,
                role=msg["role"],
                content=_extract_text(msg["content"]),
                model=model,
            )
            db.add(db_msg)
    await db.commit()

    # Build DeepSeek request
    deepseek_messages = [{"role": m["role"], "content": m["content"]} for m in messages]

    # Resolve public model name to actual DeepSeek model
    actual_model = settings.resolve_model(model)

    payload = {
        "model": actual_model,
        "messages": deepseek_messages,
        "stream": stream,
    }

    headers = settings.deepseek_headers()

    log.info(
        "Proxying to %s | model=%s | resolved=%s | messages=%d | stream=%s",
        DEEPSEEK_CHAT_URL,
        model,
        actual_model,
        len(deepseek_messages),
        stream,
    )

    async with httpx.AsyncClient(timeout=120.0) as client:
        if stream:
            async with client.stream(
                "POST", DEEPSEEK_CHAT_URL, json=payload, headers=headers
            ) as resp:
                resp.raise_for_status()
                full_content = ""
                tokens_out = 0
                tokens_in = 0

                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            yield "data: [DONE]\n\n"
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                full_content += content
                            # Track token counts from first usage chunk
                            if "usage" in chunk:
                                usage = chunk["usage"]
                                tokens_in = usage.get("prompt_tokens", 0)
                                tokens_out = usage.get("completion_tokens", 0)
                            yield f"data: {data}\n\n"
                        except json.JSONDecodeError:
                            continue

                # Log assistant response
                db_msg = Message(
                    session_id=session_id,
                    role="assistant",
                    content=full_content,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    model=model,
                )
                db.add(db_msg)
                await db.commit()
                log.info(
                    "Stream complete | session=%s | tokens_in=%d | tokens_out=%d | chars=%d",
                    session_id,
                    tokens_in,
                    tokens_out,
                    len(full_content),
                )
        else:
            resp = await client.post(
                DEEPSEEK_CHAT_URL, json=payload, headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            tokens_in = usage.get("prompt_tokens", 0)
            tokens_out = usage.get("completion_tokens", 0)

            # Log assistant response
            db_msg = Message(
                session_id=session_id,
                role="assistant",
                content=content,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                model=model,
            )
            db.add(db_msg)
            await db.commit()

            yield json.dumps(data)
