from __future__ import annotations

import sqlite3
import threading
import uuid
import json
import calendar
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from .config import default_config_dir


RECURRENCES = {
    "once", "daily", "weekdays", "weekends", "weekly",
    "monthly", "yearly", "custom",
}


@dataclass(frozen=True, slots=True)
class Reminder:
    id: int
    uid: str
    title: str
    due_at: datetime
    recurrence: str
    enabled: bool
    completed: bool
    last_triggered_at: datetime | None
    repeat_days: tuple[int, ...] = ()


def _utc_text(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.astimezone()
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def _parse_time(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


class ReminderService:
    """Thread-safe local reminders with deterministic recurrence handling."""

    def __init__(self, database_path: Path | None = None) -> None:
        self.database_path = database_path or default_config_dir() / "reminders.sqlite3"
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._schema_lock = threading.Lock()
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterable[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=10)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA journal_mode = WAL")
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._schema_lock, self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uid TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    due_at TEXT NOT NULL,
                    recurrence TEXT NOT NULL DEFAULT 'once',
                    enabled INTEGER NOT NULL DEFAULT 1,
                    completed INTEGER NOT NULL DEFAULT 0,
                    last_triggered_at TEXT,
                    created_at TEXT NOT NULL
                )"""
            )
            columns = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(reminders)").fetchall()
            }
            if "repeat_days" not in columns:
                connection.execute(
                    "ALTER TABLE reminders ADD COLUMN repeat_days TEXT NOT NULL DEFAULT '[]'"
                )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_reminders_due ON reminders(enabled, completed, due_at)"
            )

    @staticmethod
    def _from_row(row: sqlite3.Row) -> Reminder:
        return Reminder(
            id=int(row["id"]), uid=str(row["uid"]), title=str(row["title"]),
            due_at=_parse_time(row["due_at"]), recurrence=str(row["recurrence"]),
            enabled=bool(row["enabled"]), completed=bool(row["completed"]),
            last_triggered_at=_parse_time(row["last_triggered_at"]),
            repeat_days=tuple(sorted(set(json.loads(row["repeat_days"] or "[]")))),
        )

    def create(self, title: str, due_at: datetime, recurrence: str = "once",
               enabled: bool = True,
               repeat_days: Iterable[int] = ()) -> Reminder:
        title = title.strip()
        if not title:
            raise ValueError("reminder title cannot be empty")
        if recurrence not in RECURRENCES:
            raise ValueError("unsupported recurrence")
        if due_at.tzinfo is None:
            due_at = due_at.astimezone()
        days = self._validate_repeat_days(recurrence, repeat_days)
        due_at = self._align_start(due_at, recurrence, days)
        now = datetime.now(timezone.utc)
        with self._connect() as connection:
            cursor = connection.execute(
                """INSERT INTO reminders
                   (uid, title, due_at, recurrence, enabled, completed, created_at,
                    repeat_days)
                   VALUES (?, ?, ?, ?, ?, 0, ?, ?)""",
                (str(uuid.uuid4()), title, _utc_text(due_at), recurrence,
                 int(enabled), _utc_text(now), json.dumps(days)),
            )
            row = connection.execute(
                "SELECT * FROM reminders WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
        return self._from_row(row)

    def update(self, reminder_id: int, title: str, due_at: datetime,
               recurrence: str, enabled: bool = True,
               repeat_days: Iterable[int] = ()) -> bool:
        title = title.strip()
        if not title or recurrence not in RECURRENCES:
            raise ValueError("invalid reminder")
        if due_at.tzinfo is None:
            due_at = due_at.astimezone()
        days = self._validate_repeat_days(recurrence, repeat_days)
        due_at = self._align_start(due_at, recurrence, days)
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE reminders SET title = ?, due_at = ?, recurrence = ?,
                   enabled = ?, completed = 0, last_triggered_at = NULL,
                   repeat_days = ? WHERE id = ?""",
                (title, _utc_text(due_at), recurrence, int(enabled),
                 json.dumps(days), reminder_id),
            )
        return cursor.rowcount == 1

    def list_all(self) -> list[Reminder]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM reminders ORDER BY completed, due_at, id"
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def delete(self, reminder_id: int) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        return cursor.rowcount == 1

    def set_enabled(self, reminder_id: int, enabled: bool) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE reminders SET enabled = ? WHERE id = ? AND completed = 0",
                (int(enabled), reminder_id),
            )
        return cursor.rowcount == 1

    def complete(self, reminder_id: int) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE reminders SET completed = 1, enabled = 0 WHERE id = ?",
                (reminder_id,),
            )
        return cursor.rowcount == 1

    @staticmethod
    def _validate_repeat_days(recurrence: str,
                              repeat_days: Iterable[int]) -> tuple[int, ...]:
        days = tuple(sorted({int(day) for day in repeat_days}))
        if any(day < 0 or day > 6 for day in days):
            raise ValueError("repeat day must be between Monday (0) and Sunday (6)")
        if recurrence == "custom" and not days:
            raise ValueError("custom recurrence requires at least one weekday")
        return days

    @staticmethod
    def _replace_calendar_date(value: datetime, year: int, month: int,
                               day: int) -> datetime:
        last_day = calendar.monthrange(year, month)[1]
        return value.replace(year=year, month=month, day=min(day, last_day))

    @staticmethod
    def _align_start(due_at: datetime, recurrence: str,
                     repeat_days: Iterable[int] = ()) -> datetime:
        allowed: tuple[int, ...] = ()
        if recurrence == "weekdays":
            allowed = (0, 1, 2, 3, 4)
        elif recurrence == "weekends":
            allowed = (5, 6)
        elif recurrence == "custom":
            allowed = tuple(repeat_days)
        candidate = due_at
        while allowed and candidate.weekday() not in allowed:
            candidate += timedelta(days=1)
        return candidate

    @classmethod
    def _next_due(cls, due_at: datetime, recurrence: str, now: datetime,
                  repeat_days: Iterable[int] = ()) -> datetime:
        candidate = due_at.astimezone()
        local_now = now.astimezone(candidate.tzinfo)
        days = tuple(repeat_days)
        if recurrence == "weekdays":
            days = (0, 1, 2, 3, 4)
        elif recurrence == "weekends":
            days = (5, 6)

        while candidate <= local_now:
            if recurrence == "daily":
                candidate += timedelta(days=1)
            elif recurrence == "weekly":
                candidate += timedelta(days=7)
            elif recurrence in {"weekdays", "weekends", "custom"}:
                candidate += timedelta(days=1)
                while candidate.weekday() not in days:
                    candidate += timedelta(days=1)
            elif recurrence == "monthly":
                year = candidate.year + (1 if candidate.month == 12 else 0)
                month = 1 if candidate.month == 12 else candidate.month + 1
                candidate = cls._replace_calendar_date(
                    candidate, year, month, due_at.astimezone().day
                )
            elif recurrence == "yearly":
                candidate = cls._replace_calendar_date(
                    candidate, candidate.year + 1,
                    due_at.astimezone().month, due_at.astimezone().day,
                )
            else:
                raise ValueError(f"unsupported recurring schedule: {recurrence}")
        return candidate.astimezone(due_at.tzinfo)

    def claim_due(self, now: datetime | None = None) -> list[Reminder]:
        """Return reminders due once and advance/disable them in one transaction."""
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                """SELECT * FROM reminders WHERE enabled = 1 AND completed = 0
                   AND due_at <= ? ORDER BY due_at, id""",
                (_utc_text(current),),
            ).fetchall()
            reminders = [self._from_row(row) for row in rows]
            for reminder in reminders:
                if reminder.recurrence == "once":
                    connection.execute(
                        """UPDATE reminders SET enabled = 0, last_triggered_at = ?
                           WHERE id = ?""",
                        (_utc_text(current), reminder.id),
                    )
                else:
                    next_due = self._next_due(
                        reminder.due_at, reminder.recurrence, current,
                        reminder.repeat_days,
                    )
                    connection.execute(
                        """UPDATE reminders SET due_at = ?, last_triggered_at = ?
                           WHERE id = ?""",
                        (_utc_text(next_due), _utc_text(current), reminder.id),
                    )
        return reminders
