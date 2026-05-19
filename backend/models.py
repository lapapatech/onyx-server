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
    api_key = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(128), default="")
    created_at = Column(DateTime, default=_utcnow)
    last_seen = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=_new_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    model = Column(String(64), default="deepseek-chat")
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
