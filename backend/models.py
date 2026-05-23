"""SQLAlchemy models — users, sessions, messages."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def _utcnow():
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_new_id)
    name = Column(String(128), default="")
    created_at = Column(DateTime, default=_utcnow)
    last_seen = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, default=_new_id)
    key = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String(128), default="")
    active = Column(Integer, default=1)  # 1=active, 0=revoked
    created_at = Column(DateTime, default=_utcnow)
    last_used_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="api_keys")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=_new_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    model = Column(String(64), default="deepseek-chat")
    os = Column(String(32), default="")
    editor = Column(String(32), default="")
    ip_addr = Column(String(45), default="")
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False, index=True)
    role = Column(String(16), nullable=False)  # user / assistant / system
    content = Column(Text, nullable=False)
    tokens_in = Column(Integer, default=0)
    tokens_out = Column(Integer, default=0)
    model = Column(String(64), default="")
    created_at = Column(DateTime, default=_utcnow)

    session = relationship("Session", back_populates="messages")


class InviteCode(Base):
    __tablename__ = "invite_codes"

    id = Column(String, primary_key=True, default=_new_id)
    code = Column(String(32), unique=True, nullable=False, index=True)
    created_by = Column(String(128), default="admin")
    max_uses = Column(Integer, default=5)  # 0 = unlimited
    use_count = Column(Integer, default=0)
    active = Column(Integer, default=1)
    created_at = Column(DateTime, default=_utcnow)
    expires_at = Column(DateTime, nullable=True)
