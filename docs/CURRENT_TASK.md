# CURRENT TASK — World-State Backbone (and ONLY this)

## Goal
Build the persistent data layer that holds a coherent story world, so later
stages can read from it and write approved changes back. NO generation, NO
validation, NO personalization in this task.

## Pre-answered decisions (decided)
- Language: Python. Storage: SQLite (local file). No ORM.
- Storage sits behind an interface with clean, swappable signatures.

## Tables required (exact names and fields)
- `canon`: id, statement, category, immutable(bool)
- `characters`: id, name, traits(json), relationships(json), speech_style,
  history(json)
- `events`: id, order_index, summary, characters_involved(json),
  world_refs(json), created_at
- `per_child`: SCHEMA ONLY — child_id, characters_met(json), threads(json).
  Create the table but DO NOT populate it and DO NOT build any personalization
  logic on it. It is a stub for later.

## Functions required (storage behind an interface)
- `get_world_slice(character_ids=None, recent_events=N, canon_categories=None) -> dict`
- `write_events(events: list) -> None`
- `get_character(id)`, `add_character(...)`, `add_canon(...)` as needed

## Explicitly NOT in this task
- No story generation, no coherence validator, no personalization logic.
- No CLI. No TTS, no UI.

## Stop condition
Schema (exact tables/fields) + the storage interface + required functions + a
green test suite + the demo script, committed and pushed. Backbone only.
