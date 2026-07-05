# CURRENT TASK — World-State Backbone (and ONLY this)

## Goal
Build the persistent data layer that holds a coherent story world, so later
stages can read from it and write approved changes back. NO generation, NO
validation, NO personalization in this task.

## Pre-answered decisions (do NOT stop to ask — decided)
- Language: Python. Storage: SQLite (local file). No ORM needed; sqlite3 or a
  thin wrapper is fine.
- Reads return plain dataclasses. Writes go through one path only.
- Canon changes ONLY by applying an approved changeset; every canon row records
  the changeset that created/last-modified it (provenance).
- Repo: storyos-kids only.

## Scope (what "backbone" means here)
- Schema for a world and its canon: entities (character/location/item/faction/
  concept), facts (key/value attributes), relationships (typed edges), events
  (a timeline) + event participants.
- Write-back audit trail: changesets + individual changes, applied atomically.
- A read API that returns a full world-state snapshot (the "retrieve" step the
  later generation loop will call).

## Explicitly NOT in this task
- No story generation, no coherence validator, no personalization.
- No TTS, no UI, no multi-world orchestration beyond storing multiple worlds.

## Deliverables
- `worldstate/` package: `schema.sql`, `db.py`, `models.py`, `repository.py`.
- `tests/` pytest suite (CRUD, lifecycle, atomic rollback, provenance, FK
  cascade, cross-world isolation).
- `scripts/seed_demo.py`: seeds a world, retrieves state, evolves it, prints.

## Stop condition
Schema + repository API + migrations + a green test suite + the demo script,
committed and pushed to the working branch. No generation/validation/
personalization.
