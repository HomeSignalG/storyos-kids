"""SQLite connection + schema initialization for the world-state backbone.

Thin wrapper over the stdlib :mod:`sqlite3` — no ORM. Enforces foreign keys
and exposes rows as :class:`sqlite3.Row` so callers can use column names.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Union

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect(path: Union[str, Path] = ":memory:") -> sqlite3.Connection:
    """Open a connection with the pragmas the backbone relies on.

    ``path`` may be a filesystem path or ``":memory:"`` (the default, used by
    tests). The schema is created if it is not already present.
    """
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()
    return conn
