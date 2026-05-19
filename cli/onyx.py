#!/usr/bin/env python3
"""Onyx CLI — lightweight client for the Onyx backend proxy."""

import json
import os
import sys
from pathlib import Path
from typing import Optional

import httpx
import typer
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()
err_console = Console(stderr=True)

# ── defaults from env ────────────────────────────────────────────────
DEFAULT_BACKEND = os.getenv("ONYX_BACKEND_URL", "http://127.0.0.1:8000")
DEFAULT_MODEL = os.getenv("ONYX_MODEL", "onyx-flash")
API_KEY = os.getenv("ONYX_API_KEY", "")

# ── helpers ──────────────────────────────────────────────────────────


def _headers() -> dict:
    if not API_KEY:
        err_console.print("[red]Error:[/] ONYX_API_KEY not set")
        raise typer.Exit(1)
    return {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def _health_check(backend: str) -> dict:
    resp = httpx.get(f"{backend}/health", timeout=5)
    resp.raise_for_status()
    return resp.json()


def _load_file(path: str) -> str:
    p = Path(path)
    if not p.exists():
        err_console.print(f"[red]Error:[/] file not found: {path}")
        raise typer.Exit(1)
    return p.read_text(encoding="utf-8")


# ── commands ─────────────────────────────────────────────────────────


@app.callback()
def main_callback(ctx: typer.Context):
    """Onyx CLI — AI coding assistant (backend → DeepSeek)."""


@app.command()
def health(
    backend: str = typer.Option(
        DEFAULT_BACKEND, "--backend", "-b", help="Onyx backend URL"
    ),
):
    """Check backend connectivity and status."""
    try:
        status = _health_check(backend)
        model = status.get("model", "unknown")
        console.print(f"[green]✓[/] Backend [bold]{backend}[/] is healthy")
        console.print(f"   Model: [cyan]{model}[/]")
        console.print(f"   Status: {status.get('status', 'unknown')}")
    except httpx.HTTPStatusError as e:
        err_console.print(f"[red]✗[/] Backend returned {e.response.status_code}")
        raise typer.Exit(1)
    except httpx.RequestError as e:
        err_console.print(f"[red]✗[/] Cannot reach backend: {e}")
        raise typer.Exit(1)


@app.command()
def chat(
    message: str = typer.Argument(..., help="Your message or question"),
    model: str = typer.Option(DEFAULT_MODEL, "--model", "-m", help="Model to use"),
    file: Optional[str] = typer.Option(
        None, "--file", "-f", help="Include file as context"
    ),
    backend: str = typer.Option(
        DEFAULT_BACKEND, "--backend", "-b", help="Onyx backend URL"
    ),
    no_stream: bool = typer.Option(False, "--no-stream", help="Disable streaming"),
):
    """Single-turn chat with Onyx backend."""
    _do_chat(message, model, file, backend, no_stream, session_id=None)


@app.command()
def session(
    message: str = typer.Argument(..., help="Your message or question"),
    model: str = typer.Option(DEFAULT_MODEL, "--model", "-m", help="Model to use"),
    file: Optional[str] = typer.Option(
        None, "--file", "-f", help="Include file as context"
    ),
    backend: str = typer.Option(
        DEFAULT_BACKEND, "--backend", "-b", help="Onyx backend URL"
    ),
    no_stream: bool = typer.Option(False, "--no-stream", help="Disable streaming"),
    session_id: Optional[str] = typer.Option(
        None, "--session-id", help="Resume existing session"
    ),
):
    """Multi-turn chat (maintains conversation history on backend)."""
    _do_chat(message, model, file, backend, no_stream, session_id)


def _do_chat(
    message: str,
    model: str,
    file: Optional[str],
    backend: str,
    no_stream: bool,
    session_id: Optional[str],
):
    try:
        health = _health_check(backend)
    except Exception as e:
        err_console.print(f"[red]✗[/] Backend unavailable: {e}")
        err_console.print("   Start it:  uvicorn backend.main:app --port 8000")
        raise typer.Exit(1)

    # Build messages
    messages = []
    if file:
        content = _load_file(file)
        messages.append(
            {
                "role": "user",
                "content": f"Context from {file}:\n```\n{content}\n```",
            }
        )

    messages.append({"role": "user", "content": message})

    body = {
        "model": model,
        "messages": messages,
        "stream": not no_stream,
    }
    if session_id:
        body["session_id"] = session_id

    try:
        if no_stream:
            _do_sync(backend, body)
        else:
            _do_stream(backend, body)
    except httpx.HTTPStatusError as e:
        err_console.print(f"[red]Error {e.response.status_code}:[/] {e.response.text}")
        raise typer.Exit(1)
    except httpx.RequestError as e:
        err_console.print(f"[red]Network error:[/] {e}")
        raise typer.Exit(1)


def _do_sync(backend: str, body: dict):
    body["stream"] = False
    resp = httpx.post(
        f"{backend}/v1/chat/completions",
        json=body,
        headers=_headers(),
        timeout=180,
    )
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    console.print(Markdown(content))


def _do_stream(backend: str, body: dict):
    body["stream"] = True
    with httpx.Client(timeout=180) as client:
        with client.stream(
            "POST",
            f"{backend}/v1/chat/completions",
            json=body,
            headers=_headers(),
        ) as resp:
            resp.raise_for_status()
            buffer = ""
            for line in resp.iter_lines():
                if line.startswith("data: "):
                    payload = line[6:]
                    if payload.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            buffer += content
                            sys.stdout.write(content)
                            sys.stdout.flush()
                    except json.JSONDecodeError:
                        continue
            print()  # trailing newline


# ── entry ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app()
