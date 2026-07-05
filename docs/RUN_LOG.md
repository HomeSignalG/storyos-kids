# RUN LOG — World-State Backbone

A factual, chronological record of what was built this session, the decisions
made, and how it was verified.

## Session
- Date: 2026-07-05
- Branch: `claude/sources-of-truth-doc-m0e11l`
- Task: build the World-State Backbone only (see `docs/CURRENT_TASK.md`).
  Explicitly NOT generation, validation, or personalization.

## Spec history (resolved)
- `docs/CURRENT_TASK.md` first arrived truncated ("...sqlite3 or a thin"). A
  backbone was built from a reconstructed spec (worlds/entities/facts/
  relationships + a changeset write-back layer). That shape did not match the
  reviewer's intended schema.
- The real, un-truncated spec was then supplied and the schema was reconciled
  in one pass to the exact tables/fields and function signatures below. The
  earlier entity/changeset model and the read-only CLI were removed.

## Final schema (exact fields)
- `canon`: id, statement, category, immutable(bool as INTEGER 0/1)
- `characters`: id, name, traits(json), relationships(json), speech_style,
  history(json)
- `events`: id, order_index, summary, characters_involved(json),
  world_refs(json), created_at
- `per_child` — SCHEMA ONLY: child_id (PK), characters_met(json), threads(json).
  Created by the schema; no function populates it; no personalization logic.

## Storage interface (swappable)
- `worldstate/store.py` defines `WorldStore` (abstract) and `SqliteWorldStore`.
- Functions:
  - `get_world_slice(character_ids=None, recent_events=10, canon_categories=None) -> dict`
    (character_ids None -> all; recent_events None -> all, else N most recent
    returned chronologically; canon_categories None -> all)
  - `write_events(events: list) -> None` (atomic bulk append; created_at auto)
  - `get_character(id)`, `add_character(...)`, `add_canon(...)`
  - plus `get_canon`, `list_canon`, `list_characters`
- JSON columns are stored as TEXT and exposed as Python objects via dataclasses
  in `worldstate/models.py`.

## Files
- `worldstate/`: `schema.sql`, `db.py`, `models.py`, `store.py`, `__init__.py`
- `scripts/seed_demo.py` — seed canon/characters/events -> print world slices
- `tests/` — pytest suite (23 cases): schema/exact-columns, per_child stub,
  canon CRUD + immutable roundtrip + category filter, character CRUD + JSON
  roundtrip, event bulk write + defaults + atomicity, world-slice shape /
  filters / recent-N ordering / JSON-serializability, file persistence,
  interface conformance.
- Docs/config: `docs/SOURCES_OF_TRUTH.md`, `docs/CURRENT_TASK.md` (real spec),
  `README.md`, `pyproject.toml`, `.gitignore`, this `docs/RUN_LOG.md`.

## Commit timeline (branch)
1. Add SOURCES_OF_TRUTH decided-facts doc.
2. Add Operating mode section and complete Current phase line.
3. Build world-state backbone (reconstructed spec: entities + changesets).
4. Extend backbone: read helpers, provenance, audit log, export, CLI.
5. Remove CLI to keep the PR backbone-only; add run log.
6. Reconcile schema to the real spec (canon/characters/events/per_child +
   WorldStore interface); remove the entity/changeset model and CLI.

## Removed vs the real spec
- Dropped: `worlds`, `entities`, `facts`, `relationships`, `event_participants`,
  `changesets`, `changes`, provenance columns, and the read-only CLI. None of
  these are in the real spec.

## Verification
- `python -m pytest` -> 23 passed.
- `python scripts/seed_demo.py` -> prints a full slice and a focused slice;
  `per_child` reports 0 rows (stub).
- File-backed DB reopened successfully (schema persists).

## Pull request
- PR #1 targets a `main` base branch created at the repo's initial commit (the
  repository was empty; the working branch was the only/default branch).
- CI: none configured (0 workflows, 0 checks). Session subscribed to PR
  activity for reviews and any future CI.

## Status
- Halted, awaiting review. No work started past the current-phase line.
