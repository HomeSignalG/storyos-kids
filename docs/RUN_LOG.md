# RUN LOG — World-State Backbone

A factual, chronological record of what was built this session, the decisions
made, the caveats, and how it was verified. Kept honest on purpose: it records
what actually happened, including a known spec divergence.

## Session
- Date: 2026-07-05
- Branch: `claude/sources-of-truth-doc-m0e11l`
- Task: build the World-State Backbone only (see `docs/CURRENT_TASK.md`).
  Explicitly NOT generation, validation, or personalization.

## Known caveat — spec divergence (unresolved)
- `docs/CURRENT_TASK.md` arrived truncated mid-sentence ("...sqlite3 or a thin")
  and was received that way on repeated sends. The task was reconstructed from
  the stated Goal plus `docs/SOURCES_OF_TRUTH.md`.
- Follow-up review questions referenced a schema with tables named `canon`,
  `characters`, `events`, and `per_child`, and a `RUN_LOG.md` deliverable. The
  backbone as built uses a different, generic shape (see Schema below): there
  are no tables named `canon`, `characters`, or `per_child`. `per_child` was
  intentionally omitted because per-child personalization is out of scope this
  phase per `SOURCES_OF_TRUTH.md`.
- Outstanding decision for the reviewer: whether to rename/reshape the schema to
  those literal names (and whether a `per_child` storage scaffold is in scope).
  Not done unilaterally — it touches the personalization scope line.

## What was built
- `worldstate/schema.sql` — SQLite schema. Canon = `worlds`, `entities`,
  `facts`, `relationships`, `events`, `event_participants`. Write-back audit
  trail = `changesets`, `changes`. Plus `schema_meta` (version marker).
- `worldstate/db.py` — connection + schema init (stdlib `sqlite3`, no ORM),
  `PRAGMA foreign_keys = ON`.
- `worldstate/models.py` — frozen dataclasses returned by reads; `WorldState`
  snapshot.
- `worldstate/repository.py` — `WorldStateStore`. The only write path into
  canon is `propose_changeset -> stage_* -> approve_changeset ->
  apply_changeset`; apply is atomic and stamps provenance on every touched row.
  Read/audit surface: `retrieve_world_state`, `get_entity`, `list_entities`,
  `get_facts`, `get_relationships`, `get_events`, `get_event_participants`,
  `provenance`, `audit_log`, `export_world`.
- `scripts/seed_demo.py` — end-to-end demo (seed -> retrieve -> evolve -> print).
- `tests/` — pytest suite (29 cases): schema/FK/persistence, changeset
  lifecycle guards, happy path, provenance, atomic rollback, updates/deletes,
  FK cascade, cross-world isolation, read helpers, audit log, JSON export.
- Docs/config: `docs/SOURCES_OF_TRUTH.md`, `docs/CURRENT_TASK.md`, `README.md`,
  `pyproject.toml`, `.gitignore`, this `docs/RUN_LOG.md`.

## Key decisions (from SOURCES_OF_TRUTH + reconstructed task)
- Python + SQLite (local file), no ORM.
- Canon is truth; canon changes only through an approved, audited changeset.
- Facts modeled as structured key/value on entities, plus typed relationships
  and timeline events. (Chosen as the most queryable option for a later
  validator; recorded as a default, open to revision.)

## Commit timeline (branch)
1. Add SOURCES_OF_TRUTH decided-facts doc.
2. Add Operating mode section and complete Current phase line.
3. Build world-state backbone: SQLite canon + changeset write-back.
4. Extend backbone: read helpers, provenance, audit log, export, CLI.
5. Remove CLI to keep the PR strictly backbone-only; add this run log.

## CLI: added then removed
- A read-only inspection CLI (`python -m worldstate ...`) was added under a
  "go as far as you can" instruction, then removed at the reviewer's request so
  the PR is strictly backbone-only. The audit/export *methods* it used remain on
  `WorldStateStore` (they are backbone read surface, not CLI).

## Pull request
- PR #1 opened against a `main` base branch created at the repo's initial commit
  (the repository was empty; the working branch was the only/default branch).
- CI: none configured (0 GitHub Actions workflows, 0 status checks). Nothing to
  turn green or autofix. The session is subscribed to PR activity for reviews
  and any future CI.

## Verification
- `python -m pytest` -> 29 passed.
- `python scripts/seed_demo.py` -> runs; prints the seeded and evolved world
  slice (2 changesets applied).
- File-backed DB reopened successfully (schema persists, no re-init error).

## Status
- Halted, awaiting review. No work started past the current-phase line.
