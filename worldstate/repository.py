"""The world-state store: reads canon, and writes canon ONLY via changesets.

Design invariant (from docs/SOURCES_OF_TRUTH.md): the world is a database and
canon is truth. The single write path into canon is:

    propose_changeset -> stage_* -> approve_changeset -> apply_changeset

Applying an approved changeset mutates canon atomically and stamps every
touched row with the changeset id (provenance). Reads never mutate. There is
deliberately no public method that edits an entity/fact/relationship/event
outside this flow.

Creating a *world* is the one bootstrap write that precedes any changeset,
because a changeset must belong to a world.
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Iterable, Optional, Union

from . import db
from .models import (
    Change,
    Changeset,
    Entity,
    Event,
    EventParticipant,
    Fact,
    Relationship,
    World,
    WorldState,
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class WorldStateError(RuntimeError):
    """Base class for backbone errors."""


class NotFoundError(WorldStateError):
    pass


class InvalidStateError(WorldStateError):
    """Raised when a lifecycle action is attempted from the wrong state."""


class WorldStateStore:
    """Read/write access to one SQLite-backed world-state database."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    @classmethod
    def open(cls, path: Union[str, "os.PathLike[str]"] = ":memory:") -> "WorldStateStore":
        return cls(db.connect(path))

    def close(self) -> None:
        self.conn.close()

    # -- context manager -----------------------------------------------------
    def __enter__(self) -> "WorldStateStore":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # =======================================================================
    # Worlds (bootstrap writes)
    # =======================================================================

    def create_world(self, slug: str, name: str, description: str = "") -> World:
        now = _utcnow()
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO worlds(slug, name, description, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (slug, name, description, now, now),
            )
        return self.get_world(cur.lastrowid)

    def get_world(self, world_id: int) -> World:
        row = self.conn.execute(
            "SELECT * FROM worlds WHERE id = ?", (world_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"world id={world_id} not found")
        return World(**dict(row))

    def get_world_by_slug(self, slug: str) -> World:
        row = self.conn.execute(
            "SELECT * FROM worlds WHERE slug = ?", (slug,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"world slug={slug!r} not found")
        return World(**dict(row))

    def list_worlds(self) -> list[World]:
        rows = self.conn.execute("SELECT * FROM worlds ORDER BY id").fetchall()
        return [World(**dict(r)) for r in rows]

    # =======================================================================
    # Changeset lifecycle
    # =======================================================================

    def propose_changeset(
        self, world_id: int, author: str = "", note: str = ""
    ) -> Changeset:
        self.get_world(world_id)  # existence check
        now = _utcnow()
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO changesets(world_id, status, author, note, created_at) "
                "VALUES (?, 'proposed', ?, ?, ?)",
                (world_id, author, note, now),
            )
        return self.get_changeset(cur.lastrowid)

    def get_changeset(self, changeset_id: int) -> Changeset:
        row = self.conn.execute(
            "SELECT * FROM changesets WHERE id = ?", (changeset_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"changeset id={changeset_id} not found")
        return Changeset(**dict(row))

    def list_changesets(self, world_id: int) -> list[Changeset]:
        rows = self.conn.execute(
            "SELECT * FROM changesets WHERE world_id = ? ORDER BY id", (world_id,)
        ).fetchall()
        return [Changeset(**dict(r)) for r in rows]

    def get_changes(self, changeset_id: int) -> list[Change]:
        rows = self.conn.execute(
            "SELECT * FROM changes WHERE changeset_id = ? ORDER BY seq", (changeset_id,)
        ).fetchall()
        return [
            Change(
                id=r["id"],
                changeset_id=r["changeset_id"],
                seq=r["seq"],
                op=r["op"],
                target_table=r["target_table"],
                target_id=r["target_id"],
                payload=json.loads(r["payload"]),
            )
            for r in rows
        ]

    def _require_status(self, changeset_id: int, expected: str) -> Changeset:
        cs = self.get_changeset(changeset_id)
        if cs.status != expected:
            raise InvalidStateError(
                f"changeset id={changeset_id} is {cs.status!r}, expected {expected!r}"
            )
        return cs

    def approve_changeset(self, changeset_id: int) -> Changeset:
        self._require_status(changeset_id, "proposed")
        with self.conn:
            self.conn.execute(
                "UPDATE changesets SET status = 'approved', approved_at = ? WHERE id = ?",
                (_utcnow(), changeset_id),
            )
        return self.get_changeset(changeset_id)

    def reject_changeset(self, changeset_id: int) -> Changeset:
        cs = self.get_changeset(changeset_id)
        if cs.status not in ("proposed", "approved"):
            raise InvalidStateError(
                f"changeset id={changeset_id} is {cs.status!r}; only proposed/approved "
                "changesets can be rejected"
            )
        with self.conn:
            self.conn.execute(
                "UPDATE changesets SET status = 'rejected' WHERE id = ?", (changeset_id,)
            )
        return self.get_changeset(changeset_id)

    # =======================================================================
    # Staging proposed mutations onto a changeset
    # =======================================================================

    def _add_change(
        self, changeset_id: int, op: str, table: str, payload: dict
    ) -> None:
        self._require_status(changeset_id, "proposed")
        with self.conn:
            seq = self.conn.execute(
                "SELECT COALESCE(MAX(seq), 0) + 1 FROM changes WHERE changeset_id = ?",
                (changeset_id,),
            ).fetchone()[0]
            self.conn.execute(
                "INSERT INTO changes(changeset_id, seq, op, target_table, payload) "
                "VALUES (?, ?, ?, ?, ?)",
                (changeset_id, seq, op, table, json.dumps(payload)),
            )

    def stage_entity(
        self,
        changeset_id: int,
        *,
        kind: str,
        slug: str,
        name: str,
        summary: str = "",
        status: str = "active",
    ) -> None:
        self._add_change(
            changeset_id,
            "insert",
            "entities",
            {"kind": kind, "slug": slug, "name": name, "summary": summary, "status": status},
        )

    def stage_entity_update(
        self, changeset_id: int, *, slug: str, **fields: str
    ) -> None:
        payload = {"slug": slug}
        payload.update(fields)
        self._add_change(changeset_id, "update", "entities", payload)

    def stage_fact(
        self, changeset_id: int, *, entity_slug: str, key: str, value: str = ""
    ) -> None:
        self._add_change(
            changeset_id,
            "insert",
            "facts",
            {"entity_slug": entity_slug, "key": key, "value": value},
        )

    def stage_fact_update(
        self, changeset_id: int, *, entity_slug: str, key: str, value: str
    ) -> None:
        self._add_change(
            changeset_id,
            "update",
            "facts",
            {"entity_slug": entity_slug, "key": key, "value": value},
        )

    def stage_relationship(
        self,
        changeset_id: int,
        *,
        src_slug: str,
        dst_slug: str,
        kind: str,
        detail: str = "",
    ) -> None:
        self._add_change(
            changeset_id,
            "insert",
            "relationships",
            {"src_slug": src_slug, "dst_slug": dst_slug, "kind": kind, "detail": detail},
        )

    def stage_relationship_update(
        self, changeset_id: int, *, src_slug: str, dst_slug: str, kind: str, detail: str
    ) -> None:
        self._add_change(
            changeset_id,
            "update",
            "relationships",
            {"src_slug": src_slug, "dst_slug": dst_slug, "kind": kind, "detail": detail},
        )

    def stage_event(
        self,
        changeset_id: int,
        *,
        seq: int,
        title: str,
        summary: str = "",
        participants: Optional[Iterable[dict]] = None,
    ) -> None:
        """Stage a timeline event.

        ``participants`` is an optional iterable of ``{"entity_slug": ..., "role": ...}``
        applied together with the event in the same change.
        """
        self._add_change(
            changeset_id,
            "insert",
            "events",
            {
                "seq": seq,
                "title": title,
                "summary": summary,
                "participants": list(participants or []),
            },
        )

    def stage_entity_delete(self, changeset_id: int, *, slug: str) -> None:
        self._add_change(changeset_id, "delete", "entities", {"slug": slug})

    def stage_fact_delete(
        self, changeset_id: int, *, entity_slug: str, key: str
    ) -> None:
        self._add_change(
            changeset_id, "delete", "facts", {"entity_slug": entity_slug, "key": key}
        )

    def stage_relationship_delete(
        self, changeset_id: int, *, src_slug: str, dst_slug: str, kind: str
    ) -> None:
        self._add_change(
            changeset_id,
            "delete",
            "relationships",
            {"src_slug": src_slug, "dst_slug": dst_slug, "kind": kind},
        )

    def stage_event_delete(self, changeset_id: int, *, seq: int) -> None:
        self._add_change(changeset_id, "delete", "events", {"seq": seq})

    # =======================================================================
    # Applying an approved changeset (the write-back)
    # =======================================================================

    def apply_changeset(self, changeset_id: int) -> Changeset:
        cs = self._require_status(changeset_id, "approved")
        changes = self.get_changes(changeset_id)
        cache: dict[str, int] = {}  # entity slug -> id, within this world
        now = _utcnow()
        with self.conn:
            for change in changes:
                self._apply_one(cs.world_id, changeset_id, change, cache, now)
            self.conn.execute(
                "UPDATE changesets SET status = 'applied', applied_at = ? WHERE id = ?",
                (now, changeset_id),
            )
        return self.get_changeset(changeset_id)

    def _apply_one(
        self, world_id: int, cs_id: int, change: Change, cache: dict, now: str
    ) -> None:
        handler = {
            "entities": self._apply_entity,
            "facts": self._apply_fact,
            "relationships": self._apply_relationship,
            "events": self._apply_event,
        }[change.target_table]
        handler(world_id, cs_id, change, cache, now)

    def _resolve_entity(self, world_id: int, slug: str, cache: dict) -> int:
        if slug in cache:
            return cache[slug]
        row = self.conn.execute(
            "SELECT id FROM entities WHERE world_id = ? AND slug = ?", (world_id, slug)
        ).fetchone()
        if row is None:
            raise NotFoundError(
                f"entity slug={slug!r} not found in world id={world_id}"
            )
        cache[slug] = row["id"]
        return row["id"]

    def _apply_entity(self, world_id, cs_id, change, cache, now) -> None:
        p = change.payload
        if change.op == "insert":
            cur = self.conn.execute(
                "INSERT INTO entities(world_id, kind, slug, name, summary, status, "
                "created_by_changeset_id, updated_by_changeset_id, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    world_id, p["kind"], p["slug"], p["name"], p.get("summary", ""),
                    p.get("status", "active"), cs_id, cs_id, now, now,
                ),
            )
            cache[p["slug"]] = cur.lastrowid
            self.conn.execute(
                "UPDATE changes SET target_id = ? WHERE id = ?", (cur.lastrowid, change.id)
            )
        elif change.op == "update":
            entity_id = self._resolve_entity(world_id, p["slug"], cache)
            fields = {k: v for k, v in p.items() if k in ("kind", "name", "summary", "status")}
            if fields:
                assignments = ", ".join(f"{k} = ?" for k in fields)
                self.conn.execute(
                    f"UPDATE entities SET {assignments}, updated_by_changeset_id = ?, "
                    "updated_at = ? WHERE id = ?",
                    (*fields.values(), cs_id, now, entity_id),
                )
            self.conn.execute(
                "UPDATE changes SET target_id = ? WHERE id = ?", (entity_id, change.id)
            )
        elif change.op == "delete":
            entity_id = self._resolve_entity(world_id, p["slug"], cache)
            self.conn.execute("DELETE FROM entities WHERE id = ?", (entity_id,))
            cache.pop(p["slug"], None)
            self.conn.execute(
                "UPDATE changes SET target_id = ? WHERE id = ?", (entity_id, change.id)
            )

    def _apply_fact(self, world_id, cs_id, change, cache, now) -> None:
        p = change.payload
        entity_id = self._resolve_entity(world_id, p["entity_slug"], cache)
        if change.op == "insert":
            cur = self.conn.execute(
                "INSERT INTO facts(world_id, entity_id, key, value, "
                "created_by_changeset_id, updated_by_changeset_id, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (world_id, entity_id, p["key"], p.get("value", ""), cs_id, cs_id, now, now),
            )
            self.conn.execute(
                "UPDATE changes SET target_id = ? WHERE id = ?", (cur.lastrowid, change.id)
            )
        elif change.op == "update":
            row = self.conn.execute(
                "SELECT id FROM facts WHERE entity_id = ? AND key = ?",
                (entity_id, p["key"]),
            ).fetchone()
            if row is None:
                raise NotFoundError(
                    f"fact key={p['key']!r} not found for entity_slug={p['entity_slug']!r}"
                )
            self.conn.execute(
                "UPDATE facts SET value = ?, updated_by_changeset_id = ?, updated_at = ? "
                "WHERE id = ?",
                (p["value"], cs_id, now, row["id"]),
            )
            self.conn.execute(
                "UPDATE changes SET target_id = ? WHERE id = ?", (row["id"], change.id)
            )
        elif change.op == "delete":
            self.conn.execute(
                "DELETE FROM facts WHERE entity_id = ? AND key = ?",
                (entity_id, p["key"]),
            )

    def _apply_relationship(self, world_id, cs_id, change, cache, now) -> None:
        p = change.payload
        src = self._resolve_entity(world_id, p["src_slug"], cache)
        dst = self._resolve_entity(world_id, p["dst_slug"], cache)
        if change.op == "insert":
            cur = self.conn.execute(
                "INSERT INTO relationships(world_id, src_entity_id, dst_entity_id, kind, "
                "detail, created_by_changeset_id, updated_by_changeset_id, created_at, "
                "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (world_id, src, dst, p["kind"], p.get("detail", ""), cs_id, cs_id, now, now),
            )
            self.conn.execute(
                "UPDATE changes SET target_id = ? WHERE id = ?", (cur.lastrowid, change.id)
            )
        elif change.op == "update":
            self.conn.execute(
                "UPDATE relationships SET detail = ?, updated_by_changeset_id = ?, "
                "updated_at = ? WHERE src_entity_id = ? AND dst_entity_id = ? AND kind = ?",
                (p.get("detail", ""), cs_id, now, src, dst, p["kind"]),
            )
        elif change.op == "delete":
            self.conn.execute(
                "DELETE FROM relationships WHERE src_entity_id = ? AND dst_entity_id = ? "
                "AND kind = ?",
                (src, dst, p["kind"]),
            )

    def _apply_event(self, world_id, cs_id, change, cache, now) -> None:
        p = change.payload
        if change.op == "insert":
            cur = self.conn.execute(
                "INSERT INTO events(world_id, seq, title, summary, "
                "created_by_changeset_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (world_id, p["seq"], p["title"], p.get("summary", ""), cs_id, now),
            )
            event_id = cur.lastrowid
            for part in p.get("participants", []):
                entity_id = self._resolve_entity(world_id, part["entity_slug"], cache)
                self.conn.execute(
                    "INSERT INTO event_participants(event_id, entity_id, role) "
                    "VALUES (?, ?, ?)",
                    (event_id, entity_id, part.get("role", "")),
                )
            self.conn.execute(
                "UPDATE changes SET target_id = ? WHERE id = ?", (event_id, change.id)
            )
        elif change.op == "delete":
            self.conn.execute(
                "DELETE FROM events WHERE world_id = ? AND seq = ?", (world_id, p["seq"])
            )

    # =======================================================================
    # Reads (the "retrieve" side of the later generation loop)
    # =======================================================================

    def get_entity(self, world_id: int, slug: str) -> Entity:
        row = self.conn.execute(
            "SELECT * FROM entities WHERE world_id = ? AND slug = ?", (world_id, slug)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"entity slug={slug!r} not found in world id={world_id}")
        return Entity(**dict(row))

    def list_entities(
        self, world_id: int, kind: Optional[str] = None
    ) -> list[Entity]:
        if kind is None:
            rows = self.conn.execute(
                "SELECT * FROM entities WHERE world_id = ? ORDER BY id", (world_id,)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM entities WHERE world_id = ? AND kind = ? ORDER BY id",
                (world_id, kind),
            ).fetchall()
        return [Entity(**dict(r)) for r in rows]

    def get_facts(self, entity_id: int) -> list[Fact]:
        rows = self.conn.execute(
            "SELECT * FROM facts WHERE entity_id = ? ORDER BY key", (entity_id,)
        ).fetchall()
        return [Fact(**dict(r)) for r in rows]

    def get_relationships(
        self, entity_id: int, direction: str = "out"
    ) -> list[Relationship]:
        """Relationships touching an entity. ``direction`` is out/in/both."""
        if direction == "out":
            where, args = "src_entity_id = ?", (entity_id,)
        elif direction == "in":
            where, args = "dst_entity_id = ?", (entity_id,)
        elif direction == "both":
            where, args = "src_entity_id = ? OR dst_entity_id = ?", (entity_id, entity_id)
        else:
            raise ValueError(f"direction must be out/in/both, got {direction!r}")
        rows = self.conn.execute(
            f"SELECT * FROM relationships WHERE {where} ORDER BY id", args
        ).fetchall()
        return [Relationship(**dict(r)) for r in rows]

    def get_events(self, world_id: int) -> list[Event]:
        rows = self.conn.execute(
            "SELECT * FROM events WHERE world_id = ? ORDER BY seq", (world_id,)
        ).fetchall()
        return [Event(**dict(r)) for r in rows]

    def get_event_participants(self, event_id: int) -> list[EventParticipant]:
        rows = self.conn.execute(
            "SELECT * FROM event_participants WHERE event_id = ? ORDER BY id", (event_id,)
        ).fetchall()
        return [EventParticipant(**dict(r)) for r in rows]

    def retrieve_world_state(self, world_id: int) -> WorldState:
        """Full canon snapshot for a world — the read the generation loop uses."""
        world = self.get_world(world_id)
        entities = [
            Entity(**dict(r))
            for r in self.conn.execute(
                "SELECT * FROM entities WHERE world_id = ? ORDER BY id", (world_id,)
            ).fetchall()
        ]
        facts = [
            Fact(**dict(r))
            for r in self.conn.execute(
                "SELECT * FROM facts WHERE world_id = ? ORDER BY entity_id, key", (world_id,)
            ).fetchall()
        ]
        relationships = [
            Relationship(**dict(r))
            for r in self.conn.execute(
                "SELECT * FROM relationships WHERE world_id = ? ORDER BY id", (world_id,)
            ).fetchall()
        ]
        events = [
            Event(**dict(r))
            for r in self.conn.execute(
                "SELECT * FROM events WHERE world_id = ? ORDER BY seq", (world_id,)
            ).fetchall()
        ]
        event_ids = [e.id for e in events]
        participants: list[EventParticipant] = []
        if event_ids:
            placeholders = ",".join("?" for _ in event_ids)
            participants = [
                EventParticipant(**dict(r))
                for r in self.conn.execute(
                    f"SELECT * FROM event_participants WHERE event_id IN ({placeholders}) "
                    "ORDER BY event_id, id",
                    event_ids,
                ).fetchall()
            ]
        return WorldState(
            world=world,
            entities=entities,
            facts=facts,
            relationships=relationships,
            events=events,
            event_participants=participants,
        )

    # =======================================================================
    # Audit / provenance and export
    # =======================================================================

    _PROVENANCE_TABLES = ("entities", "facts", "relationships")

    def provenance(self, table: str, row_id: int) -> dict:
        """The changesets that created and last modified a canon row.

        Returns ``{"created_by": Changeset|None, "updated_by": Changeset|None}``.
        ``events`` are append-only, so only ``created_by`` is populated for them.
        """
        if table == "events":
            row = self.conn.execute(
                "SELECT created_by_changeset_id FROM events WHERE id = ?", (row_id,)
            ).fetchone()
            if row is None:
                raise NotFoundError(f"events row id={row_id} not found")
            created = row["created_by_changeset_id"]
            return {
                "created_by": self.get_changeset(created) if created else None,
                "updated_by": None,
            }
        if table not in self._PROVENANCE_TABLES:
            raise ValueError(f"no provenance tracked for table {table!r}")
        row = self.conn.execute(
            f"SELECT created_by_changeset_id, updated_by_changeset_id "
            f"FROM {table} WHERE id = ?",
            (row_id,),
        ).fetchone()
        if row is None:
            raise NotFoundError(f"{table} row id={row_id} not found")
        created = row["created_by_changeset_id"]
        updated = row["updated_by_changeset_id"]
        return {
            "created_by": self.get_changeset(created) if created else None,
            "updated_by": self.get_changeset(updated) if updated else None,
        }

    def audit_log(self, world_id: int) -> list[dict]:
        """Flat, ordered record of every applied change in a world.

        One dict per change: changeset metadata joined with the change. This is
        the audit surface the later batch-ahead-with-audit stage reads.
        """
        rows = self.conn.execute(
            "SELECT c.id AS change_id, c.seq, c.op, c.target_table, c.target_id, "
            "c.payload, cs.id AS changeset_id, cs.author, cs.note, cs.applied_at "
            "FROM changes c JOIN changesets cs ON cs.id = c.changeset_id "
            "WHERE cs.world_id = ? AND cs.status = 'applied' "
            "ORDER BY cs.id, c.seq",
            (world_id,),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["payload"] = json.loads(d["payload"])
            out.append(d)
        return out

    def export_world(self, world_id: int) -> dict:
        """A JSON-serializable snapshot of a world's full canon."""
        state = self.retrieve_world_state(world_id)
        return {
            "world": asdict(state.world),
            "entities": [asdict(e) for e in state.entities],
            "facts": [asdict(f) for f in state.facts],
            "relationships": [asdict(r) for r in state.relationships],
            "events": [asdict(ev) for ev in state.events],
            "event_participants": [asdict(p) for p in state.event_participants],
        }
