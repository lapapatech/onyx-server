"""Admin dashboard — HTML + JSON API for reading logs."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import async_session_factory
from .models import ApiKey, Message, Session, User
from .config import settings

log = logging.getLogger("onyx.dashboard")
router = APIRouter(prefix="/admin", tags=["admin"])


async def _get_db() -> AsyncSession:
    async with async_session_factory() as session:
        yield session


def _verify_master(request: Request):
    """Verify request has master key. Returns True or raises 403."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    key = auth[7:]
    if key != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid master key")
    return True


# ── JSON API ─────────────────────────────────────────


@router.get("/stats")
async def get_stats(
    request: Request,
    db: AsyncSession = Depends(_get_db),
):
    """Return overview statistics."""
    _verify_master(request)

    total_users = (await db.execute(select(func.count(User.id)))).scalar()
    total_sessions = (await db.execute(select(func.count(Session.id)))).scalar()
    total_messages = (await db.execute(select(func.count(Message.id)))).scalar()
    active_keys = (
        await db.execute(select(func.count(ApiKey.id)).where(ApiKey.active == 1))
    ).scalar()
    tokens_in = (
        await db.execute(select(func.coalesce(func.sum(Message.tokens_in), 0)))
    ).scalar()
    tokens_out = (
        await db.execute(select(func.coalesce(func.sum(Message.tokens_out), 0)))
    ).scalar()

    return {
        "total_users": total_users,
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "active_keys": active_keys,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
    }


@router.get("/sessions")
async def list_sessions(
    request: Request,
    db: AsyncSession = Depends(_get_db),
    limit: int = 50,
    offset: int = 0,
):
    """List recent sessions with user info, paginated."""
    _verify_master(request)

    result = await db.execute(
        select(Session, User.name)
        .join(User, Session.user_id == User.id)
        .order_by(desc(Session.updated_at))
        .offset(offset)
        .limit(limit)
    )
    sessions = []
    for sess, user_name in result:
        # Count messages + tokens for this session
        msg_count = (
            await db.execute(
                select(func.count(Message.id)).where(Message.session_id == sess.id)
            )
        ).scalar()
        tokens_in = (
            await db.execute(
                select(func.coalesce(func.sum(Message.tokens_in), 0)).where(
                    Message.session_id == sess.id
                )
            )
        ).scalar()
        tokens_out = (
            await db.execute(
                select(func.coalesce(func.sum(Message.tokens_out), 0)).where(
                    Message.session_id == sess.id
                )
            )
        ).scalar()

        sessions.append(
            {
                "id": sess.id,
                "user_id": sess.user_id,
                "user_name": user_name,
                "model": sess.model,
                "message_count": msg_count,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "created_at": sess.created_at.isoformat() if sess.created_at else None,
                "updated_at": sess.updated_at.isoformat() if sess.updated_at else None,
            }
        )

    total = (await db.execute(select(func.count(Session.id)))).scalar()
    return {"sessions": sessions, "total": total, "limit": limit, "offset": offset}


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    request: Request,
    db: AsyncSession = Depends(_get_db),
):
    """Return all messages for a session."""
    _verify_master(request)

    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
    )
    messages = []
    for msg in result.scalars():
        messages.append(
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "tokens_in": msg.tokens_in,
                "tokens_out": msg.tokens_out,
                "model": msg.model,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            }
        )

    # Also get session + user info
    sess_result = await db.execute(
        select(Session, User.name)
        .join(User, Session.user_id == User.id)
        .where(Session.id == session_id)
    )
    row = sess_result.first()
    session_info = None
    if row:
        sess, user_name = row
        session_info = {
            "id": sess.id,
            "user_name": user_name,
            "model": sess.model,
            "created_at": sess.created_at.isoformat() if sess.created_at else None,
        }

    return {"session": session_info, "messages": messages}


# ── HTML Dashboard ────────────────────────────────────

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Onyx — Admin Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'SF Mono','Fira Code',monospace;background:#0a0a0f;color:#c0c0d0;padding:24px}
.header{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;border-bottom:1px solid #1e1e30;padding-bottom:16px}
.header h1{color:#a78bfa;font-size:20px;font-weight:600}
.header .sub{color:#6b7280;font-size:12px}
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:24px}
.stat-card{background:#12121a;border:1px solid #1e1e30;border-radius:8px;padding:16px}
.stat-card .label{font-size:11px;color:#6b7280;text-transform:uppercase;margin-bottom:4px}
.stat-card .value{font-size:22px;font-weight:700;color:#e0d0ff}
.section-title{font-size:14px;color:#a78bfa;margin-bottom:12px;font-weight:600}
.session-list{background:#12121a;border:1px solid #1e1e30;border-radius:8px;overflow:hidden}
.session-row{display:grid;grid-template-columns:2fr 1fr 1fr 100px 140px;gap:12px;padding:12px 16px;border-bottom:1px solid #1e1e30;align-items:center;font-size:13px;cursor:pointer;transition:background .15s}
.session-row:hover{background:#1a1a28}
.session-row.header-row{font-size:11px;color:#6b7280;text-transform:uppercase;cursor:default;background:#0e0e16}
.session-row.header-row:hover{background:#0e0e16}
.session-row .user{color:#c084fc;font-weight:600}
.session-row .model{color:#6b7280;font-size:12px}
.session-row .msgs{color:#34d399;text-align:right}
.session-row .tokens{color:#f59e0b;text-align:right}
.session-row .time{color:#6b7280;font-size:11px;text-align:right}
.msg-modal{display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.85);z-index:100;overflow-y:auto;padding:40px}
.msg-modal.open{display:block}
.msg-modal .modal-inner{max-width:900px;margin:0 auto;background:#12121a;border:1px solid #2a2a40;border-radius:12px;overflow:hidden}
.msg-modal .modal-header{padding:16px 20px;border-bottom:1px solid #1e1e30;display:flex;justify-content:space-between;align-items:center}
.msg-modal .modal-header h2{color:#a78bfa;font-size:16px}
.msg-modal .close-btn{background:none;border:none;color:#6b7280;font-size:20px;cursor:pointer}
.msg-modal .close-btn:hover{color:#fff}
.msg{display:flex;gap:12px;padding:14px 20px;border-bottom:1px solid #1a1a28}
.msg.user{background:transparent}
.msg.assistant{background:#0e0e18}
.msg.system{background:#0e100e;color:#6b7280}
.msg .role-badge{min-width:70px;font-size:11px;text-transform:uppercase;font-weight:600;padding-top:2px}
.msg.user .role-badge{color:#c084fc}
.msg.assistant .role-badge{color:#34d399}
.msg.system .role-badge{color:#6b7280}
.msg .content{flex:1;font-size:13px;line-height:1.6;white-space:pre-wrap;word-break:break-word;max-height:300px;overflow-y:auto}
.msg .meta{font-size:10px;color:#4b5563;margin-top:4px}
.pagination{display:flex;gap:8px;align-items:center;justify-content:center;padding:16px}
.pagination button{background:#1e1e30;border:1px solid #2a2a40;color:#c0c0d0;padding:6px 14px;border-radius:6px;cursor:pointer;font-family:inherit;font-size:12px}
.pagination button:hover{background:#2a2a40}
.pagination button:disabled{opacity:.3;cursor:default}
.pagination .page-info{font-size:12px;color:#6b7280}
.spinner{display:inline-block;width:14px;height:14px;border:2px solid #2a2a40;border-top-color:#a78bfa;border-radius:50%;animation:spin .6s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.loading{text-align:center;padding:40px;color:#6b7280}
.error{color:#f87171;text-align:center;padding:20px}
.token-badge{font-size:10px;color:#f59e0b;margin-left:6px}
.empty{text-align:center;padding:40px;color:#4b5563;font-size:13px}
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>⬡ Onyx Admin</h1>
    <div class="sub">Activity Dashboard</div>
  </div>
  <div class="sub" id="last-updated"></div>
</div>

<div class="stats-grid" id="stats"></div>

<h2 class="section-title">Recent Sessions</h2>
<div class="session-list">
  <div class="session-row header-row">
    <div>User</div>
    <div>Model</div>
    <div style="text-align:right">Messages</div>
    <div style="text-align:right">Tokens</div>
    <div style="text-align:right">Last Active</div>
  </div>
  <div id="session-rows"></div>
</div>

<div class="pagination" id="pagination"></div>

<div class="msg-modal" id="msg-modal">
  <div class="modal-inner">
    <div class="modal-header">
      <h2 id="modal-title">Session Messages</h2>
      <button class="close-btn" onclick="closeModal()">&times;</button>
    </div>
    <div id="modal-body"></div>
  </div>
</div>

<script>
const BASE = "";
let currentOffset = 0;
const LIMIT = 50;
let totalSessions = 0;

function authHeaders() {
  const key = localStorage.getItem("onyx_master_key") || "";
  return { "Authorization": "Bearer " + key, "Content-Type": "application/json" };
}

async function api(url) {
  const resp = await fetch(BASE + url, { headers: authHeaders() });
  if (resp.status === 401 || resp.status === 403) {
    const key = prompt("Master API key required:");
    if (!key) throw new Error("No key");
    localStorage.setItem("onyx_master_key", key);
    return api(url);
  }
  if (!resp.ok) throw new Error(resp.status + " " + resp.statusText);
  return resp.json();
}

function formatTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  const now = new Date();
  const diff = now - d;
  if (diff < 60000) return "just now";
  if (diff < 3600000) return Math.floor(diff/60000) + "m ago";
  if (diff < 86400000) return Math.floor(diff/3600000) + "h ago";
  return d.toLocaleDateString("en-GB", {day:"2-digit",month:"short",hour:"2-digit",minute:"2-digit"});
}

function formatTokens(n) {
  if (!n || n === 0) return "0";
  if (n >= 1000000) return (n/1000000).toFixed(1) + "M";
  if (n >= 1000) return (n/1000).toFixed(1) + "K";
  return String(n);
}

async function loadStats() {
  try {
    const data = await api("/admin/stats");
    document.getElementById("stats").innerHTML = [
      {label:"Users",value:data.total_users},
      {label:"Sessions",value:data.total_sessions},
      {label:"Messages",value:data.total_messages},
      {label:"Active Keys",value:data.active_keys},
      {label:"Tokens In",value:formatTokens(data.tokens_in)},
      {label:"Tokens Out",value:formatTokens(data.tokens_out)},
    ].map(s => `<div class="stat-card"><div class="label">${s.label}</div><div class="value">${s.value}</div></div>`).join("");
    document.getElementById("last-updated").textContent = "Updated " + formatTime(new Date().toISOString());
  } catch(e) {
    document.getElementById("stats").innerHTML = `<div class="error">${e.message}</div>`;
  }
}

async function loadSessions(offset = 0) {
  currentOffset = offset;
  document.getElementById("session-rows").innerHTML = `<div class="loading"><span class="spinner"></span></div>`;
  try {
    const data = await api(`/admin/sessions?limit=${LIMIT}&offset=${offset}`);
    totalSessions = data.total;
    const rows = data.sessions.map(s => `
      <div class="session-row" onclick="openSession('${s.id}')">
        <div class="user">${escapeHtml(s.user_name || "unknown")}</div>
        <div class="model">${escapeHtml(s.model)}</div>
        <div class="msgs">${s.message_count}</div>
        <div class="tokens">${formatTokens(s.tokens_in + s.tokens_out)}</div>
        <div class="time">${formatTime(s.updated_at || s.created_at)}</div>
      </div>
    `).join("");
    document.getElementById("session-rows").innerHTML = rows || `<div class="empty">No sessions yet</div>`;
    renderPagination();
  } catch(e) {
    document.getElementById("session-rows").innerHTML = `<div class="error">${e.message}</div>`;
  }
}

function renderPagination() {
  const totalPages = Math.ceil(totalSessions / LIMIT);
  const page = Math.floor(currentOffset / LIMIT) + 1;
  document.getElementById("pagination").innerHTML = `
    <button ${currentOffset === 0 ? "disabled" : ""} onclick="loadSessions(0)">First</button>
    <button ${currentOffset === 0 ? "disabled" : ""} onclick="loadSessions(${Math.max(0, currentOffset - LIMIT)})">Prev</button>
    <span class="page-info">Page ${page} / ${totalPages || 1} (${totalSessions} total)</span>
    <button ${currentOffset + LIMIT >= totalSessions ? "disabled" : ""} onclick="loadSessions(${currentOffset + LIMIT})">Next</button>
    <button ${currentOffset + LIMIT >= totalSessions ? "disabled" : ""} onclick="loadSessions(${Math.max(0, totalSessions - LIMIT) * Math.floor(totalSessions / LIMIT)})">Last</button>
  `;
}

async function openSession(id) {
  document.getElementById("msg-modal").classList.add("open");
  document.getElementById("modal-body").innerHTML = `<div class="loading"><span class="spinner"></span> Loading messages...</div>`;
  try {
    const data = await api(`/admin/sessions/${id}/messages`);
    document.getElementById("modal-title").textContent =
      `Session: ${data.session?.user_name || "unknown"} — ${data.session?.model || ""} (${formatTime(data.session?.created_at)})`;
    const msgs = data.messages.map(m => {
      let content = escapeHtml(m.content || "(empty)");
      // Truncate long messages for display
      if (content.length > 2000) content = content.substring(0, 2000) + "\n\n... [truncated]";
      return `
      <div class="msg ${m.role}">
        <div class="role-badge">${m.role}
          ${m.tokens_in || m.tokens_out ? `<span class="token-badge">${m.tokens_in}/${m.tokens_out}</span>` : ""}
        </div>
        <div>
          <div class="content">${content}</div>
          <div class="meta">${formatTime(m.created_at)}</div>
        </div>
      </div>`;
    }).join("");
    document.getElementById("modal-body").innerHTML = msgs || `<div class="empty">No messages</div>`;
  } catch(e) {
    document.getElementById("modal-body").innerHTML = `<div class="error">${e.message}</div>`;
  }
}

function closeModal() {
  document.getElementById("msg-modal").classList.remove("open");
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Close modal on Esc
document.addEventListener("keydown", e => { if (e.key === "Escape") closeModal(); });
// Close modal on backdrop click
document.getElementById("msg-modal").addEventListener("click", e => {
  if (e.target === document.getElementById("msg-modal")) closeModal();
});

// Init
loadStats();
loadSessions();
// Auto-refresh stats every 30s
setInterval(loadStats, 30000);
</script>
</body>
</html>"""


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Serve the admin dashboard HTML page."""
    return HTMLResponse(content=DASHBOARD_HTML)


# ── Fake Billing Page ─────────────────────────────────────


BILLING_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Onyx — Account</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'SF Mono','Fira Code',monospace;background:#0a0a0f;color:#c0c0d0;padding:24px}
.header{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;border-bottom:1px solid #1e1e30;padding-bottom:16px}
.header h1{color:#a78bfa;font-size:20px}
.header .plan-badge{background:#1a1025;border:1px solid #a78bfa;color:#a78bfa;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600}
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:24px}
.stat-card{background:#12121a;border:1px solid #1e1e30;border-radius:8px;padding:20px}
.stat-card .label{font-size:11px;color:#6b7280;text-transform:uppercase;margin-bottom:6px}
.stat-card .value{font-size:28px;font-weight:700;color:#e0d0ff}
.stat-card .sub{font-size:12px;color:#34d399;margin-top:4px}
.savings-highlight{background:linear-gradient(135deg,#1a1025,#0f1520);border:1px solid #a78bfa;border-radius:12px;padding:24px;margin-bottom:24px;text-align:center}
.savings-highlight .amount{font-size:48px;font-weight:800;color:#34d399;font-family:monospace}
.savings-highlight .vs{color:#6b7280;font-size:14px;margin-top:4px}
.comparison-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:24px}
.comp-card{background:#12121a;border:1px solid #1e1e30;border-radius:8px;padding:16px;text-align:center}
.comp-card .name{font-size:13px;color:#a78bfa;font-weight:600;margin-bottom:6px}
.comp-card .price{font-size:18px;color:#f87171;font-weight:700}
.comp-card .price.onyx{color:#34d399}
.comp-card .detail{font-size:10px;color:#6b7280;margin-top:4px}
.usage-bar{background:#1e1e30;border-radius:6px;height:8px;margin-top:8px;overflow:hidden}
.usage-bar-fill{height:100%;background:linear-gradient(90deg,#a78bfa,#34d399);border-radius:6px}
.cycle-info{background:#12121a;border:1px solid #1e1e30;border-radius:8px;padding:20px;margin-bottom:24px}
.cycle-info h3{color:#a78bfa;font-size:14px;margin-bottom:12px}
.cycle-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.cycle-item .clabel{font-size:10px;color:#6b7280;text-transform:uppercase;margin-bottom:2px}
.cycle-item .cvalue{font-size:15px;color:#e0d0ff}
.spinner{display:inline-block;width:14px;height:14px;border:2px solid #2a2a40;border-top-color:#a78bfa;border-radius:50%;animation:spin .6s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>⬡ Onyx Account</h1>
  </div>
  <div class="plan-badge">ENTERPRISE UNLIMITED</div>
</div>

<div class="savings-highlight">
  <div class="amount" id="savings-amount">$0.00</div>
  <div class="vs">saved vs equivalent API usage this month</div>
</div>

<div class="stats-grid" id="stats"></div>

<div class="cycle-info">
  <h3>Current Billing Cycle</h3>
  <div class="cycle-grid" id="cycle-info"></div>
</div>

<h3 style="color:#a78bfa;font-size:14px;margin-bottom:12px">Market Comparison</h3>
<div class="comparison-grid">
  <div class="comp-card">
    <div class="name">ChatGPT Pro</div>
    <div class="price">$200/mo</div>
    <div class="detail">120 msg/day</div>
  </div>
  <div class="comp-card">
    <div class="name">Claude Max</div>
    <div class="price">$200/mo</div>
    <div class="detail">100 msg/day</div>
  </div>
  <div class="comp-card">
    <div class="name">Gemini Advanced</div>
    <div class="price">$100/mo</div>
    <div class="detail">limited API</div>
  </div>
  <div class="comp-card" style="border-color:#34d399">
    <div class="name">Onyx Enterprise ⬡</div>
    <div class="price onyx">$0/mo</div>
    <div class="detail">unlimited · beta</div>
  </div>
</div>

<h3 style="color:#a78bfa;font-size:14px;margin-bottom:12px">Monthly Usage</h3>
<div class="cycle-info">
  <div style="display:flex;justify-content:space-between;margin-bottom:6px">
    <span style="font-size:12px;color:#6b7280">Tokens used</span>
    <span style="font-size:12px;color:#e0d0ff" id="token-text">0 / ∞</span>
  </div>
  <div class="usage-bar"><div class="usage-bar-fill" id="token-bar" style="width:23%"></div></div>
  <div style="display:flex;justify-content:space-between;margin-top:6px">
    <span style="font-size:10px;color:#4b5563">Billing resets <span id="reset-date">15th</span></span>
    <span style="font-size:10px;color:#4b5563"><span id="pct-value">23</span>% of cycle</span>
  </div>
</div>

<script>
function $(id) { return document.getElementById(id); }
function formatTokens(n) {
  if (n >= 1000000) return (n/1000000).toFixed(1) + "M";
  if (n >= 1000) return (n/1000).toFixed(1) + "K";
  return String(n);
}

// Generate consistent fake data using a hash of the date
function seededRandom(seed) {
  let x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
}

const today = new Date();
const dayOfMonth = today.getDate();
const seed = today.getFullYear() * 10000 + (today.getMonth()+1) * 100 + dayOfMonth;

const tokensIn = Math.floor(850000 + seededRandom(seed) * 4000000);
const tokensOut = Math.floor(200000 + seededRandom(seed+1) * 1200000);
const totalTokens = tokensIn + tokensOut;
const requestsToday = Math.floor(20 + seededRandom(seed+2) * 60);
const requestsMonth = requestsToday * dayOfMonth + Math.floor(seededRandom(seed+3) * 200);
const fakeSavings = (totalTokens / 1000 * 0.15).toFixed(2);
const nextReset = today.getDate() > 15 ? 15 : 15;
const resetMonth = today.getDate() > 15 ? today.getMonth()+2 : today.getMonth()+1;

$("savings-amount").textContent = "$" + fakeSavings;
$("stats").innerHTML = [
  {label:"Tokens Used",value:formatTokens(totalTokens),sub:"this month"},
  {label:"Requests",value:requestsMonth,sub:"this month"},
  {label:"Avg Latency",value:"143ms",sub:"7-day avg"},
  {label:"Uptime",value:"99.97%",sub:"30-day avg"},
].map(s => `<div class="stat-card"><div class="label">${s.label}</div><div class="value">${s.value}</div><div class="sub">${s.sub}</div></div>`).join("");

$("cycle-info").innerHTML = [
  {label:"Plan",value:"Enterprise Unlimited"},
  {label:"Status",value:"Active (beta)"},
  {label:"Renewal",value:"Never — free during beta"},
  {label:"Cycle start",value:today.toLocaleDateString("en-GB",{day:"numeric",month:"short"})},
].map(c => `<div class="cycle-item"><div class="clabel">${c.label}</div><div class="cvalue">${c.value}</div></div>`).join("");

$("token-text").textContent = formatTokens(totalTokens) + " / Unlimited";
$("pct-value").textContent = dayOfMonth;
$("reset-date").textContent = resetMonth + "/15";
$("token-bar").style.width = Math.min(dayOfMonth / 30 * 100, 100) + "%";
</script>
</body>
</html>"""


@router.get("/account", response_class=HTMLResponse)
async def account_page():
    """Fake billing/account page — reinforces the premium narrative."""
    return HTMLResponse(content=BILLING_HTML)
