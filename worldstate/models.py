"""Dataclasses mirroring the world-state schema.

These are plain read models: the repository returns them from queries. Writes
never go through these objects directly — canon only changes by applying an
approved changeset (see :mod:`worldstate.repository`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# Allowed vocabularies, kept in sync with schema.sql CHECK constraints.
ENTITY_KINDS = ("character", "location", "item", "faction", "concept")
ENTITY_STATUSES = ("active", "archived")
CHANGESET_STATUSES = ("proposed", "approved", "applied", "rejected")
CHANGE_OPS = ("insert", "update", "delete")
CHANGE_TABLES = ("entities", "facts", "relationships", "events", "event_participants")


@dataclass(frozen=True)
class World:
    id: int
    slug: str
    name: str
    description: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Entity:
    id: int
    world_id: int
    kind: str
    slug: str
    name: str
    summary: str
    status: str
    created_by_changeset_id: Optional[int]
    updated_by_changeset_id: Optional[int]
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Fact:
    id: int
    world_id: int
    entity_id: int
    key: str
    value: str
    created_by_changeset_id: Optional[int]
    updated_by_changeset_id: Optional[int]
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Relationship:
    id: int
    world_id: int
    src_entity_id: int
    dst_entity_id: int
    kind: str
    detail: str
    created_by_changeset_id: Optional[int]
    updated_by_changeset_id: Optional[int]
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Event:
    id: int
    world_id: int
    seq: int
    title: str
    summary: str
    created_by_changeset_id: Optional[int]
    created_at: str


@dataclass(frozen=True)
class EventParticipant:
    id: int
    event_id: int
    entity_id: int
    role: str


@dataclass(frozen=True)
class Changeset:
    id: int
    world_id: int
    status: str
    author: str
    note: str
    created_at: str
    approved_at: Optional[str]
    applied_at: Optional[str]


@dataclass(frozen=True)
class Change:
    id: int
    changeset_id: int
    seq: int
    op: str
    target_table: str
    target_id: Optional[int]
    payload: dict


@dataclass
class WorldState:
    """A full snapshot of one world's canon, as read back for later stages."""

    world: World
    entities: list[Entity] = field(default_factory=list)
    facts: list[Fact] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    event_participants: list[EventParticipant] = field(default_factory=list)

    def entity_by_slug(self, slug: str) -> Optional[Entity]:
        for e in self.entities:
            if e.slug == slug:
                return e
        return None

    def facts_for(self, entity_id: int) -> list[Fact]:
        return [f for f in self.facts if f.entity_id == entity_id]
