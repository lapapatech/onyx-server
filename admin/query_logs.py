#!/usr/bin/env python3
"""Onyx Admin — query logged data from the backend database.

Usage:
    python3 admin/query_logs.py --recent          Last 20 messages
    python3 admin/query_logs.py --users           List all users
    python3 admin/query_logs.py --user <id>       Messages for a user
    python3 admin/query_logs.py --search <text>   Search message content
    python3 admin/query_logs.py --stats           Token usage stats
"""

import argparse
import sqlite3
import sys
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "onyx.db"


def conn() -> sqlite3.Connection:
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}", file=sys.stderr)
        sys.exit(1)
    return sqlite3.connect(str(DB_PATH))


def cmd_recent(limit: int = 20):
    db = conn()
    cur = db.execute("""
        SELECT m.id, u.name, m.role, substr(m.content, 1, 80),
               m.tokens_in, m.tokens_out, m.created_at
        FROM messages m
        JOIN sessions s ON m.session_id = s.id
        JOIN users u ON s.user_id = u.id
        ORDER BY m.id DESC
        LIMIT ?
    """, (limit,))
    print(f"{'ID':>5} {'USER':<16} {'ROLE':<10} {'CONTENT':<50} {'TOKENS':<12} TIME")
    print("-" * 120)
    for row in cur:
        print(f"{row[0]:>5} {row[1][:16]:<16} {row[2]:<10} {row[3][:50]:<50} {row[4]}/{row[5]:<6} {row[6][:19]}")


def cmd_users():
    db = conn()
    cur = db.execute("""
        SELECT u.id, u.api_key, u.name, u.created_at, u.last_seen,
               (SELECT COUNT(*) FROM sessions s WHERE s.user_id = u.id) as sessions,
               (SELECT COUNT(*) FROM messages m JOIN sessions s ON m.session_id = s.id WHERE s.user_id = u.id) as msgs
        FROM users u
        ORDER BY u.created_at DESC
    """)
    print(f"{'ID':<14} {'API KEY':<24} {'NAME':<16} {'SESSIONS':<10} {'MESSAGES':<10} CREATED")
    print("-" * 100)
    for row in cur:
        print(f"{row[0]:<14} {row[1][:22]:<24} {str(row[2] or '')[:14]:<16} {row[4]:<10} {row[6]:<10} {row[3][:19]}")


def cmd_user(user_id: str):
    db = conn()
    cur = db.execute("""
        SELECT m.id, m.role, substr(m.content, 1, 120), m.tokens_in, m.tokens_out, m.created_at
        FROM messages m
        JOIN sessions s ON m.session_id = s.id
        WHERE s.user_id = ?
        ORDER BY m.id
    """, (user_id,))
    print(f"Messages for user {user_id}:")
    print("-" * 100)
    for row in cur:
        print(f"  [{row[1]:<10}] {row[2][:80]:<80} ({row[3]}/{row[4]} tok)")


def cmd_search(text: str):
    db = conn()
    cur = db.execute("""
        SELECT m.id, u.name, m.role, substr(m.content, 1, 120), m.created_at
        FROM messages m
        JOIN sessions s ON m.session_id = s.id
        JOIN users u ON s.user_id = u.id
        WHERE m.content LIKE ?
        ORDER BY m.id DESC
        LIMIT 20
    """, (f"%{text}%",))
    found = False
    for row in cur:
        found = True
        print(f"[{row[3][:80]}] — {row[1]} ({row[2]}) @ {row[4][:19]}")
    if not found:
        print("No matches.")


def cmd_stats():
    db = conn()
    cur = db.execute("""
        SELECT COUNT(*), COALESCE(SUM(tokens_in), 0), COALESCE(SUM(tokens_out), 0)
        FROM messages
    """)
    total, tok_in, tok_out = cur.fetchone()
    cur2 = db.execute("SELECT COUNT(DISTINCT user_id) FROM sessions")
    users = cur2.fetchone()[0]
    cur3 = db.execute("SELECT COUNT(*) FROM sessions")
    sessions = cur3.fetchone()[0]

    print(f"Total messages: {total}")
    print(f"Total users:    {users}")
    print(f"Total sessions: {sessions}")
    print(f"Tokens in:      {tok_in:,}")
    print(f"Tokens out:     {tok_out:,}")
    print(f"Total tokens:   {tok_in + tok_out:,}")


def main():
    parser = argparse.ArgumentParser(description="Onyx Admin — query logs")
    parser.add_argument("--recent", type=int, nargs="?", const=20, help="Show recent N messages")
    parser.add_argument("--users", action="store_true", help="List users")
    parser.add_argument("--user", type=str, help="Show messages for user ID")
    parser.add_argument("--search", type=str, help="Search message content")
    parser.add_argument("--stats", action="store_true", help="Token usage stats")
    args = parser.parse_args()

    if args.recent:
        cmd_recent(args.recent)
    elif args.users:
        cmd_users()
    elif args.user:
        cmd_user(args.user)
    elif args.search:
        cmd_search(args.search)
    elif args.stats:
        cmd_stats()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
