"""Dataclasses mirroring the world-state schema.

JSON-typed columns are exposed here as native Python objects (lists/dicts);
the store handles serialization to/from TEXT.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Canon:
    id: int
    statement: str
    category: str
    immutable: bool


@dataclass
class Character:
    id: int
    name: str
    traits: list = field(default_factory=list)          # json
    relationships: dict = field(default_factory=dict)   # json
    speech_style: str = ""
    history: list = field(default_factory=list)          # json


@dataclass
class Event:
    id: int
    order_index: int
    summary: str
    characters_involved: list = field(default_factory=list)  # json
    world_refs: list = field(default_factory=list)            # json
    created_at: str = ""


@dataclass
class PerChild:
    """Schema-only stub. No function populates this; here for completeness."""

    child_id: str
    characters_met: list = field(default_factory=list)  # json
    threads: list = field(default_factory=list)          # json
