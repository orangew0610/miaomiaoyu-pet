from __future__ import annotations

import json
import re
import sqlite3
import threading
import uuid
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .config import default_config_dir

MEMORY_KINDS = {"short_term", "episodic", "preference", "summary"}
ROLES = {"user", "assistant", "system"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True, slots=True)
class MemoryEntry:
    id: int
    character_id: str
    session_id: str
    role: str
    content: str
    created_at: str
    kind: str
    source_ids: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class ContextBundle:
    system_prompt: str
    messages: tuple[dict[str, str], ...]
    injected_memory_ids: tuple[int, ...]
    estimated_tokens: int


class MemoryService(ABC):
    @abstractmethod
    def add_message(self, character_id: str, session_id: str, role: str,
                    content: str, *, kind: str = "short_term",
                    source_ids: Iterable[int] = ()) -> MemoryEntry:
        raise NotImplementedError

    @abstractmethod
    def recent_messages(self, character_id: str, limit: int = 20) -> list[MemoryEntry]:
        raise NotImplementedError

    @abstractmethod
    def search(self, character_id: str, query: str, limit: int = 8,
               session_id: str | None = None) -> list[MemoryEntry]:
        raise NotImplementedError

    @abstractmethod
    def build_context(self, character_id: str, current_query: str,
                      character_prompt: str, *, budget_tokens: int = 3000) -> ContextBundle:
        raise NotImplementedError


class SQLiteMemoryService(MemoryService):
    """SQLite memory using one connection per operation for worker-thread safety."""

    def __init__(self, database_path: Path | None = None) -> None:
        self.database_path = database_path or default_config_dir() / "memory.sqlite3"
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._schema_lock = threading.Lock()
        self._fts_available = False
        self._initialize()

    @property
    def fts_available(self) -> bool:
        return self._fts_available

    @contextmanager
    def _connect(self) -> Iterable[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=10)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA busy_timeout = 5000")
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._schema_lock, self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS memory_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    character_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    kind TEXT NOT NULL DEFAULT 'short_term',
                    source_ids TEXT NOT NULL DEFAULT '[]',
                    deleted_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_memory_character_time
                    ON memory_entries(character_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_memory_session
                    ON memory_entries(character_id, session_id, id);
                CREATE TABLE IF NOT EXISTS memory_settings (
                    character_id TEXT PRIMARY KEY,
                    enabled INTEGER NOT NULL DEFAULT 1
                );
                """
            )
            try:
                connection.executescript(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                        content, content='memory_entries', content_rowid='id', tokenize='unicode61'
                    );
                    CREATE TRIGGER IF NOT EXISTS memory_ai AFTER INSERT ON memory_entries BEGIN
                        INSERT INTO memory_fts(rowid, content) VALUES (new.id, new.content);
                    END;
                    CREATE TRIGGER IF NOT EXISTS memory_ad AFTER DELETE ON memory_entries BEGIN
                        INSERT INTO memory_fts(memory_fts, rowid, content)
                        VALUES('delete', old.id, old.content);
                    END;
                    CREATE TRIGGER IF NOT EXISTS memory_au AFTER UPDATE OF content ON memory_entries BEGIN
                        INSERT INTO memory_fts(memory_fts, rowid, content)
                        VALUES('delete', old.id, old.content);
                        INSERT INTO memory_fts(rowid, content) VALUES (new.id, new.content);
                    END;
                    """
                )
                connection.execute("INSERT INTO memory_fts(memory_fts) VALUES('rebuild')")
                self._fts_available = True
            except sqlite3.OperationalError:
                self._fts_available = False

    def new_session_id(self) -> str:
        return str(uuid.uuid4())

    def is_enabled(self, character_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT enabled FROM memory_settings WHERE character_id = ?", (character_id,)
            ).fetchone()
        return True if row is None else bool(row["enabled"])

    def set_enabled(self, character_id: str, enabled: bool) -> None:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO memory_settings(character_id, enabled) VALUES(?, ?)
                   ON CONFLICT(character_id) DO UPDATE SET enabled=excluded.enabled""",
                (character_id, int(enabled)),
            )

    def add_message(self, character_id: str, session_id: str, role: str,
                    content: str, *, kind: str = "short_term",
                    source_ids: Iterable[int] = ()) -> MemoryEntry:
        if role not in ROLES:
            raise ValueError(f"unsupported role: {role}")
        if kind not in MEMORY_KINDS:
            raise ValueError(f"unsupported memory kind: {kind}")
        content = content.strip()
        if not content:
            raise ValueError("memory content cannot be empty")
        created_at = utc_now()
        if not self.is_enabled(character_id):
            return MemoryEntry(0, character_id, session_id, role, content, created_at, kind)
        encoded_sources = json.dumps([int(item) for item in source_ids])
        with self._connect() as connection:
            cursor = connection.execute(
                """INSERT INTO memory_entries
                   (character_id, session_id, role, content, created_at, kind, source_ids)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (character_id, session_id, role, content, created_at, kind, encoded_sources),
            )
            entry_id = int(cursor.lastrowid)
        return MemoryEntry(entry_id, character_id, session_id, role, content,
                           created_at, kind, tuple(json.loads(encoded_sources)))

    def _rows_to_entries(self, rows: Iterable[sqlite3.Row]) -> list[MemoryEntry]:
        return [MemoryEntry(int(row["id"]), row["character_id"], row["session_id"],
                            row["role"], row["content"], row["created_at"], row["kind"],
                            tuple(json.loads(row["source_ids"] or "[]"))) for row in rows]

    def recent_messages(self, character_id: str, limit: int = 20,
                        session_id: str | None = None) -> list[MemoryEntry]:
        if not self.is_enabled(character_id):
            return []
        session_sql = " AND session_id = ?" if session_id else ""
        parameters: list[Any] = [character_id]
        if session_id:
            parameters.append(session_id)
        parameters.append(limit)
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT * FROM memory_entries WHERE character_id = ? AND deleted_at IS NULL
                   AND kind = 'short_term' AND role IN ('user', 'assistant')
                """ + session_sql + " ORDER BY id DESC LIMIT ?", parameters
            ).fetchall()
        return list(reversed(self._rows_to_entries(rows)))

    def latest_session_id(self, character_id: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT session_id FROM memory_entries
                   WHERE character_id = ? AND deleted_at IS NULL
                   AND ((kind = 'short_term' AND role IN ('user', 'assistant'))
                        OR (kind IN ('preference', 'episodic')
                            AND session_id != 'manual'))
                   ORDER BY id DESC LIMIT 1""",
                (character_id,),
            ).fetchone()
        return str(row["session_id"]) if row else None

    def list_conversation_sessions(self, character_id: str,
                                   limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT session_id,
                          SUM(CASE WHEN kind = 'short_term' THEN 1 ELSE 0 END)
                              AS message_count,
                          MAX(id) AS last_id, MAX(created_at) AS updated_at
                   FROM memory_entries
                   WHERE character_id = ? AND deleted_at IS NULL
                   AND ((kind = 'short_term' AND role IN ('user', 'assistant'))
                        OR (kind IN ('preference', 'episodic')
                            AND session_id != 'manual'))
                   GROUP BY session_id ORDER BY last_id DESC LIMIT ?""",
                (character_id, limit),
            ).fetchall()
            sessions = []
            for row in rows:
                preview = connection.execute(
                    """SELECT content FROM memory_entries WHERE id = ?""",
                    (row["last_id"],),
                ).fetchone()
                sessions.append({
                    "session_id": str(row["session_id"]),
                    "message_count": int(row["message_count"]),
                    "updated_at": str(row["updated_at"]),
                    "preview": str(preview["content"]) if preview else "",
                })
        return sessions

    @staticmethod
    def _query_terms(query: str) -> list[str]:
        return [term for term in re.findall(r"[\w\u4e00-\u9fff]+", query.lower())
                if len(term) > 1][:12]

    def search(self, character_id: str, query: str, limit: int = 8,
               session_id: str | None = None) -> list[MemoryEntry]:
        if not self.is_enabled(character_id):
            return []
        terms = self._query_terms(query)
        if not terms:
            return []
        with self._connect() as connection:
            rows: list[sqlite3.Row] = []
            scope_sql = (
                " AND (m.kind NOT IN ('preference', 'episodic') "
                "OR m.session_id = 'manual' OR m.session_id = ?)"
                if session_id else
                " AND (m.kind NOT IN ('preference', 'episodic') "
                "OR m.session_id = 'manual')"
            )
            scope_parameters = (session_id,) if session_id else ()
            if self._fts_available:
                match = " OR ".join(f'"{term}"' for term in terms)
                try:
                    rows = connection.execute(
                        f"""SELECT m.* FROM memory_fts f JOIN memory_entries m ON m.id = f.rowid
                           WHERE memory_fts MATCH ? AND m.character_id = ? AND m.deleted_at IS NULL
                           {scope_sql}
                           ORDER BY bm25(memory_fts), m.id DESC LIMIT ?""",
                        (match, character_id, *scope_parameters, limit),
                    ).fetchall()
                except sqlite3.OperationalError:
                    rows = []
            # unicode61 does not segment every CJK phrase as users expect.
            # A no-hit FTS query therefore falls back to safe substring search.
            if not rows:
                clauses = " OR ".join("content LIKE ?" for _ in terms)
                plain_scope_sql = scope_sql.replace("m.", "")
                rows = connection.execute(
                    f"""SELECT * FROM memory_entries WHERE character_id = ? AND deleted_at IS NULL
                         AND ({clauses}) {plain_scope_sql} ORDER BY id DESC LIMIT ?""",
                    (character_id, *(f"%{term}%" for term in terms),
                     *scope_parameters, limit),
                ).fetchall()
        return self._rows_to_entries(rows)

    def list_entries(self, character_id: str, *, kinds: Iterable[str] | None = None,
                     limit: int = 200) -> list[MemoryEntry]:
        parameters: list[Any] = [character_id]
        selected = list(kinds or [])
        kind_sql = ""
        if selected:
            kind_sql = f" AND kind IN ({','.join('?' for _ in selected)})"
            parameters.extend(selected)
        parameters.append(limit)
        with self._connect() as connection:
            rows = connection.execute(
                f"""SELECT * FROM memory_entries WHERE character_id = ? AND deleted_at IS NULL
                     {kind_sql} ORDER BY id DESC LIMIT ?""", parameters
            ).fetchall()
        return self._rows_to_entries(rows)

    def update_entry(self, entry_id: int, character_id: str, content: str) -> bool:
        content = content.strip()
        if not content:
            raise ValueError("memory content cannot be empty")
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE memory_entries SET content = ? WHERE id = ?
                   AND character_id = ? AND deleted_at IS NULL""",
                (content, entry_id, character_id),
            )
            if cursor.rowcount == 1:
                self._invalidate_summaries(connection, character_id, entry_id)
        return cursor.rowcount == 1

    def delete_entry(self, entry_id: int, character_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE memory_entries SET deleted_at = ? WHERE id = ?
                   AND character_id = ? AND deleted_at IS NULL""",
                (utc_now(), entry_id, character_id),
            )
            if cursor.rowcount == 1:
                self._invalidate_summaries(connection, character_id, entry_id)
        return cursor.rowcount == 1

    def delete_conversation_session(self, character_id: str, session_id: str) -> int:
        """Soft-delete one conversation save and summaries derived from it."""
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE memory_entries SET deleted_at = ?
                   WHERE character_id = ? AND session_id = ?
                   AND kind IN ('short_term', 'preference', 'episodic')
                   AND deleted_at IS NULL""",
                (utc_now(), character_id, session_id),
            )
            if cursor.rowcount:
                connection.execute(
                    """UPDATE memory_entries SET deleted_at = ?
                       WHERE character_id = ? AND kind = 'summary'
                       AND deleted_at IS NULL""",
                    (utc_now(), character_id),
                )
        return cursor.rowcount

    def _invalidate_summaries(self, connection: sqlite3.Connection,
                              character_id: str, source_id: int) -> None:
        summaries = connection.execute(
            """SELECT id, source_ids FROM memory_entries WHERE character_id = ?
               AND kind = 'summary' AND deleted_at IS NULL""",
            (character_id,),
        ).fetchall()
        affected = [int(row["id"]) for row in summaries
                    if source_id in set(json.loads(row["source_ids"] or "[]"))]
        if affected:
            connection.execute(
                f"""UPDATE memory_entries SET deleted_at = ?
                     WHERE id IN ({','.join('?' for _ in affected)})""",
                (utc_now(), *affected),
            )

    def clear(self, character_id: str) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE memory_entries SET deleted_at = ?
                   WHERE character_id = ? AND deleted_at IS NULL""",
                (utc_now(), character_id),
            )
        return cursor.rowcount

    def add_user_memory(self, character_id: str, content: str, kind: str,
                        session_id: str | None = None) -> MemoryEntry:
        if kind not in {"episodic", "preference"}:
            raise ValueError("user-managed memory must be episodic or preference")
        if not self.is_enabled(character_id):
            raise RuntimeError("记忆已关闭，无法新增长期记忆")
        return self.add_message(
            character_id, session_id or "manual", "user", content, kind=kind
        )

    def _ensure_extractive_summary(self, character_id: str,
                                   recent_ids: set[int]) -> MemoryEntry | None:
        with self._connect() as connection:
            existing = connection.execute(
                """SELECT * FROM memory_entries WHERE character_id = ? AND kind = 'summary'
                   AND deleted_at IS NULL ORDER BY id DESC LIMIT 1""", (character_id,)
            ).fetchone()
            covered = set(json.loads(existing["source_ids"])) if existing else set()
            rows = connection.execute(
                """SELECT * FROM memory_entries WHERE character_id = ? AND kind = 'short_term'
                   AND deleted_at IS NULL ORDER BY id ASC""", (character_id,)
            ).fetchall()
        candidates = [row for row in rows if row["id"] not in recent_ids
                      and row["id"] not in covered]
        if len(candidates) < 12:
            return self._rows_to_entries([existing])[0] if existing else None
        selected = candidates[-20:]
        source_ids = [int(row["id"]) for row in selected]
        lines = [f"[source:{row['id']}] {row['role']}: {row['content'][:240]}"
                 for row in selected]
        return self.add_message(character_id, "summary", "system", "\n".join(lines),
                                kind="summary", source_ids=source_ids)

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        return max(1, (len(text) + 2) // 3)

    def build_context(self, character_id: str, current_query: str,
                      character_prompt: str, *, budget_tokens: int = 3000,
                      session_id: str | None = None) -> ContextBundle:
        if not self.is_enabled(character_id):
            messages = ({"role": "user", "content": current_query},)
            return ContextBundle(character_prompt, messages, (),
                                 self._estimate_tokens(character_prompt + current_query))
        recent = self.recent_messages(
            character_id, limit=16, session_id=session_id
        )
        recent_ids = {entry.id for entry in recent}
        summary = self._ensure_extractive_summary(character_id, recent_ids)
        relevant = [entry for entry in self.search(
            character_id, current_query, 10, session_id=session_id
        )
                    if entry.id not in recent_ids and (
                        not session_id or entry.kind != "short_term"
                    )]
        managed = [
            entry for entry in self.list_entries(
                character_id, kinds=("preference", "episodic"), limit=100
            )
            if entry.session_id == "manual" or entry.session_id == session_id
        ][:20]
        candidates: list[MemoryEntry] = []
        seen: set[int] = set()
        for entry in [*managed, *relevant, *([summary] if summary else [])]:
            if entry and entry.id not in seen:
                seen.add(entry.id)
                candidates.append(entry)
        prompt_parts = [character_prompt]
        used_ids: list[int] = []
        token_count = self._estimate_tokens(character_prompt)
        reserve = self._estimate_tokens(current_query) + 100
        # The character prompt may legitimately occupy more than 45% of the
        # context budget.  The old absolute 45% ceiling then rejected every
        # memory even though ample total budget remained.  Allow managed and
        # retrieved memories to use the next portion of the real budget while
        # retaining room for recent dialogue and the current turn.
        memory_ceiling = min(int(budget_tokens * 0.70), budget_tokens - reserve)
        memory_lines = []
        for entry in candidates:
            label = {"preference": "用户偏好", "episodic": "情景记忆",
                     "summary": "历史摘录"}.get(entry.kind, "相关记忆")
            line = f"[{label} memory:{entry.id}] {entry.content}"
            cost = self._estimate_tokens(line)
            if token_count + cost > memory_ceiling:
                continue
            memory_lines.append(line)
            used_ids.append(entry.id)
            token_count += cost
        if memory_lines:
            prompt_parts.append(
                "以下内容来自真实保存的对话或用户编辑的记忆；编号用于事实追溯。"
                "这些是关于用户的已知事实；当用户询问自己的偏好、经历或要求回忆时，"
                "应优先依据相关记忆直接回答。不要补写其中没有的经历：\n"
                + "\n".join(memory_lines)
            )
        output: list[dict[str, str]] = []
        for entry in recent:
            cost = self._estimate_tokens(entry.content)
            if token_count + cost > budget_tokens - reserve:
                continue
            output.append({"role": entry.role, "content": entry.content})
            token_count += cost
        if not output or output[-1]["content"] != current_query:
            output.append({"role": "user", "content": current_query})
            token_count += self._estimate_tokens(current_query)
        return ContextBundle("\n\n".join(prompt_parts), tuple(output),
                             tuple(used_ids), token_count)


class NullMemoryService(MemoryService):
    def add_message(self, character_id, session_id, role, content, *,
                    kind="short_term", source_ids=()):
        return MemoryEntry(0, character_id, session_id, role, content, utc_now(), kind)

    def recent_messages(self, character_id: str, limit: int = 20,
                        session_id: str | None = None) -> list[MemoryEntry]:
        return []

    def search(self, character_id: str, query: str, limit: int = 8,
               session_id: str | None = None) -> list[MemoryEntry]:
        return []

    def build_context(self, character_id, current_query, character_prompt, *,
                      budget_tokens=3000, session_id=None):
        return ContextBundle(character_prompt,
                             ({"role": "user", "content": current_query},), (), 0)

    def delete_conversation_session(self, character_id, session_id):
        return 0
