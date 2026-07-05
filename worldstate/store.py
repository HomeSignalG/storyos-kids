"""World-state storage: an interface plus a SQLite implementation.

The interface (:class:`WorldStore`) keeps signatures clean and swappable so a
different backend can be dropped in later. Backbone only — reads and writes of
canon/characters/events. No generation, validation, or personalization; the
``per_child`` table is a schema-only stub and no method here touches it.
"""

from __future__ import annotations

import json
import os
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional, Union

from . import db
from .models import Canon, Character, Event


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class NotFoundError(LookupError):
    """Raised when a requested row does not exist."""


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------

class WorldStore(ABC):
    """Swappable storage interface for the world-state backbone."""

    @abstractmethod
    def add_canon(self, statement: str, category: str, immutable: bool = False) -> Canon:
        ...

    @abstractmethod
    def get_canon(self, canon_id: int) -> Canon:
        ...

    @abstractmethod
    def list_canon(self, categories: Optional[list] = None) -> list[Canon]:
        ...

    @abstractmethod
    def add_character(
        self,
        name: str,
        traits: Optional[list] = None,
        relationships: Optional[dict] = None,
        speech_style: str = "",
        history: Optional[list] = None,
    ) -> Character:
        ...

    @abstractmethod
    def get_character(self, id: int) -> Character:
        ...

    @abstractmethod
    def list_characters(self, character_ids: Optional[list] = None) -> list[Character]:
        ...

    @abstractmethod
    def write_events(self, events: list) -> None:
        ...

    @abstractmethod
    def get_world_slice(
        self,
        character_ids: Optional[list] = None,
        recent_events: Optional[int] = 10,
        canon_categories: Optional[list] = None,
    ) -> dict:
        ...


# ---------------------------------------------------------------------------
# SQLite implementation
# ---------------------------------------------------------------------------

class SqliteWorldStore(WorldStore):
    """SQLite-backed :class:`WorldStore`."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    @classmethod
    def open(cls, path: Union[str, "os.PathLike[str]"] = ":memory:") -> "SqliteWorldStore":
        return cls(db.connect(path))

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "SqliteWorldStore":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- row -> model --------------------------------------------------------

    @staticmethod
    def _canon(row: sqlite3.Row) -> Canon:
        return Canon(
            id=row["id"],
            statement=row["statement"],
            category=row["category"],
            immutable=bool(row["immutable"]),
        )

    @staticmethod
    def _character(row: sqlite3.Row) -> Character:
        return Character(
            id=row["id"],
            name=row["name"],
            traits=json.loads(row["traits"]),
            relationships=json.loads(row["relationships"]),
            speech_style=row["speech_style"],
            history=json.loads(row["history"]),
        )

    @staticmethod
    def _event(row: sqlite3.Row) -> Event:
        return Event(
            id=row["id"],
            order_index=row["order_index"],
            summary=row["summary"],
            characters_involved=json.loads(row["characters_involved"]),
            world_refs=json.loads(row["world_refs"]),
            created_at=row["created_at"],
        )

    # -- canon ---------------------------------------------------------------

    def add_canon(self, statement: str, category: str, immutable: bool = False) -> Canon:
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO canon(statement, category, immutable) VALUES (?, ?, ?)",
                (statement, category, 1 if immutable else 0),
            )
        return self.get_canon(cur.lastrowid)

    def get_canon(self, canon_id: int) -> Canon:
        row = self.conn.execute("SELECT * FROM canon WHERE id = ?", (canon_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"canon id={canon_id} not found")
        return self._canon(row)

    def list_canon(self, categories: Optional[list] = None) -> list[Canon]:
        if categories:
            placeholders = ",".join("?" for _ in categories)
            rows = self.conn.execute(
                f"SELECT * FROM canon WHERE category IN ({placeholders}) ORDER BY id",
                list(categories),
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM canon ORDER BY id").fetchall()
        return [self._canon(r) for r in rows]

    # -- characters ----------------------------------------------------------

    def add_character(
        self,
        name: str,
        traits: Optional[list] = None,
        relationships: Optional[dict] = None,
        speech_style: str = "",
        history: Optional[list] = None,
    ) -> Character:
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO characters(name, traits, relationships, speech_style, history) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    name,
                    json.dumps(traits if traits is not None else []),
                    json.dumps(relationships if relationships is not None else {}),
                    speech_style,
                    json.dumps(history if history is not None else []),
                ),
            )
        return self.get_character(cur.lastrowid)

    def get_character(self, id: int) -> Character:
        row = self.conn.execute("SELECT * FROM characters WHERE id = ?", (id,)).fetchone()
        if row is None:
            raise NotFoundError(f"character id={id} not found")
        return self._character(row)

    def list_characters(self, character_ids: Optional[list] = None) -> list[Character]:
        if character_ids is not None:
            if not character_ids:
                return []
            placeholders = ",".join("?" for _ in character_ids)
            rows = self.conn.execute(
                f"SELECT * FROM characters WHERE id IN ({placeholders}) ORDER BY id",
                list(character_ids),
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM characters ORDER BY id").fetchall()
        return [self._character(r) for r in rows]

    # -- events --------------------------------------------------------------

    def write_events(self, events: list) -> None:
        """Append events. Each item is a dict or an :class:`Event`.

        Recognized keys: ``order_index`` (required), ``summary`` (required),
        ``characters_involved`` (list), ``world_refs`` (list), ``created_at``
        (optional; defaulted to now). Written atomically.
        """
        now = _utcnow()
        rows = []
        for ev in events:
            d = asdict(ev) if isinstance(ev, Event) else dict(ev)
            rows.append(
                (
                    d["order_index"],
                    d["summary"],
                    json.dumps(d.get("characters_involved", []) or []),
                    json.dumps(d.get("world_refs", []) or []),
                    d.get("created_at") or now,
                )
            )
        with self.conn:
            self.conn.executemany(
                "INSERT INTO events(order_index, summary, characters_involved, "
                "world_refs, created_at) VALUES (?, ?, ?, ?, ?)",
                rows,
            )

    def _recent_events(self, recent_events: Optional[int]) -> list[Event]:
        if recent_events is None:
            rows = self.conn.execute(
                "SELECT * FROM events ORDER BY order_index, id"
            ).fetchall()
            return [self._event(r) for r in rows]
        rows = self.conn.execute(
            "SELECT * FROM events ORDER BY order_index DESC, id DESC LIMIT ?",
            (recent_events,),
        ).fetchall()
        # return chronological (ascending) order
        return [self._event(r) for r in reversed(rows)]

    # -- the retrieve step ---------------------------------------------------

    def get_world_slice(
        self,
        character_ids: Optional[list] = None,
        recent_events: Optional[int] = 10,
        canon_categories: Optional[list] = None,
    ) -> dict:
        """A JSON-serializable slice of the world for later stages.

        - ``character_ids=None`` -> all characters; a list -> just those ids.
        - ``recent_events=N`` -> the N most recent events (chronological);
          ``None`` -> all events.
        - ``canon_categories=None`` -> all canon; a list -> just those categories.
        """
        return {
            "canon": [asdict(c) for c in self.list_canon(canon_categories)],
            "characters": [asdict(c) for c in self.list_characters(character_ids)],
            "events": [asdict(e) for e in self._recent_events(recent_events)],
        }
