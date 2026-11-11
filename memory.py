"""Small SQLite conversation memory with UTC timestamps and lexical recall."""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STOP_WORDS = {
    "about", "after", "again", "also", "and", "are", "been", "before", "being",
    "can", "could", "did", "does", "for", "from", "have", "how", "into", "its",
    "just", "more", "most", "much", "please", "should", "that", "the", "their",
    "them", "then", "there", "these", "this", "those", "through", "what", "when",
    "where", "which", "with", "would", "your", "you", "tell", "show", "find",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]{2,}", text.lower()) if token not in STOP_WORDS}


class SQLiteMemory:
    def __init__(self, db_path: str | Path = "data/recallsearch.sqlite3") -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL,
                    sources_json TEXT NOT NULL DEFAULT '[]',
                    searched_web INTEGER NOT NULL DEFAULT 0
                )"""
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_session_time ON messages(session_id, id DESC)"
            )

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        sources_json: str = "[]",
        searched_web: bool = False,
    ) -> int:
        if role not in {"user", "assistant"}:
            raise ValueError("role must be 'user' or 'assistant'")
        if not session_id or not content.strip():
            raise ValueError("session_id and non-empty content are required")
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO messages(session_id, role, content, created_at_utc, sources_json, searched_web) VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, role, content, utc_now_iso(), sources_json, int(searched_web)),
            )
            return int(cursor.lastrowid)

    def list_messages(self, session_id: str, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, max(1, min(limit, 500))),
            ).fetchall()
        return [dict(row) for row in reversed(rows)]

    def recent_context(self, session_id: str, limit: int = 8) -> list[dict[str, str]]:
        rows = self.list_messages(session_id, limit=limit)
        return [{"role": row["role"], "content": row["content"]} for row in rows]

    def relevant_questions(self, session_id: str, query: str, limit: int = 4) -> list[dict[str, Any]]:
        query_tokens = _tokens(query)
        if not query_tokens:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, content, created_at_utc FROM messages WHERE session_id = ? AND role = 'user' ORDER BY id DESC LIMIT 200",
                (session_id,),
            ).fetchall()

        ranked: list[tuple[float, dict[str, Any]]] = []
        for row in rows:
            text_tokens = _tokens(row["content"])
            overlap = len(query_tokens & text_tokens)
            if not overlap:
                continue
            # Favor precise matches, while a recency tie-break helps short queries.
            score = overlap / max(1, len(query_tokens | text_tokens))
            ranked.append((score, dict(row)))
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in ranked[: max(1, min(limit, 10))]]

    def memory_context(self, session_id: str, query: str) -> str:
        questions = self.relevant_questions(session_id, query)
        if not questions:
            return ""
        lines = ["Past user questions (UTC timestamps; newest relevant matches first):"]
        for item in questions:
            lines.append(f"- [{item['created_at_utc']}] {item['content'][:500]}")
        return "\n".join(lines)

    def clear_session(self, session_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
