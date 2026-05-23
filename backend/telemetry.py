"""Lightweight telemetry — extract fingerprinting data from HTTP requests.

No changes to the CLI required. Everything is extracted server-side from
headers and request metadata that the CLI already sends.
"""

import logging
from fastapi import Request

log = logging.getLogger("onyx.telemetry")

# Known User-Agent patterns for OS detection
OS_SIGNATURES = [
    ("Windows NT 10.0", "Windows 10/11"),
    ("Windows NT 6.3", "Windows 8.1"),
    ("Windows NT 6.1", "Windows 7"),
    ("Mac OS X", "macOS"),
    ("Android", "Android"),
    ("iPhone", "iOS"),
    ("iPad", "iOS"),
    ("CrOS", "ChromeOS"),
    ("Linux", "Linux"),
]


def detect_os(user_agent: str) -> str:
    """Infer OS from User-Agent string."""
    if not user_agent:
        return "unknown"
    for sig, label in OS_SIGNATURES:
        if sig in user_agent:
            return label
    return "unknown"


def detect_editor(user_agent: str) -> str:
    """Infer editor/terminal from User-Agent."""
    if not user_agent:
        return "unknown"
    ua = user_agent.lower()
    if "vscode" in ua:
        return "vscode"
    if "jetbrains" in ua or "intellij" in ua:
        return "jetbrains"
    if "terminal" in ua or "iterm" in ua:
        return "terminal"
    if "warp" in ua:
        return "warp"
    if "cursor" in ua:
        return "cursor"
    return "terminal"  # default assumption


def extract_telemetry(request: Request) -> dict:
    """Extract telemetry fingerprint from an incoming request."""
    user_agent = request.headers.get("User-Agent", "")
    return {
        "ip": request.client.host if request.client else "unknown",
        "user_agent": user_agent[:256],
        "os": detect_os(user_agent),
        "editor": detect_editor(user_agent),
        "accept_language": request.headers.get("Accept-Language", "")[:64],
    }
