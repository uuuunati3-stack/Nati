from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from .types import Message


class Memory:
    """Small, portable SQLite transcript store; no external database is required."""

    def __init__(self, path: str = "~/.autonomous-coder/memory.sqlite3") -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.execute("CREATE TABLE IF NOT EXISTS sessions (id INTEGER PRIMARY KEY, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        self.db.execute("CREATE TABLE IF NOT EXISTS messages (session_id INTEGER, position INTEGER, role TEXT, content TEXT, name TEXT, tool_call_id TEXT)")
        self.db.commit()

    def new_session(self) -> int:
        cur = self.db.execute("INSERT INTO sessions DEFAULT VALUES")
        self.db.commit()
        return int(cur.lastrowid)

    def append(self, session_id: int, message: Message) -> None:
        position = self.db.execute("SELECT COALESCE(MAX(position), -1) + 1 FROM messages WHERE session_id=?", (session_id,)).fetchone()[0]
        self.db.execute("INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?)", (session_id, position, message.role, message.content, message.name, message.tool_call_id))
        self.db.commit()

    def load(self, session_id: int, limit: int = 100) -> list[Message]:
        rows = self.db.execute("SELECT role, content, name, tool_call_id FROM messages WHERE session_id=? ORDER BY position DESC LIMIT ?", (session_id, limit)).fetchall()
        return [Message(role=r[0], content=r[1], name=r[2], tool_call_id=r[3]) for r in reversed(rows)]

    def search(self, query: str, limit: int = 10) -> list[Message]:
        rows = self.db.execute("SELECT role, content, name, tool_call_id FROM messages WHERE content LIKE ? ORDER BY rowid DESC LIMIT ?", (f"%{query}%", limit)).fetchall()
        return [Message(role=r[0], content=r[1], name=r[2], tool_call_id=r[3]) for r in rows]
