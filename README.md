# storyos-kids — World-State Backbone

Persistent canon layer for coherent, evolving kids' bedtime story worlds.

> The world is a **database**. The AI is a **renderer**. Canon is truth.
> See [`docs/SOURCES_OF_TRUTH.md`](docs/SOURCES_OF_TRUTH.md) and
> [`docs/CURRENT_TASK.md`](docs/CURRENT_TASK.md).

This repository currently contains **only** the world-state backbone: the
schema and a swappable storage interface. No generation, validation, or
personalization. `per_child` exists as a schema-only stub for later.

## Layout

```
worldstate/
  schema.sql       SQLite schema: canon, characters, events, per_child (stub)
  db.py            connection + schema init
  models.py        dataclasses (JSON fields exposed as Python objects)
  store.py         WorldStore interface + SqliteWorldStore implementation
scripts/
  seed_demo.py     end-to-end demonstration
tests/             pytest suite
```

## Schema (exact fields)

- **canon**: `id, statement, category, immutable(bool)`
- **characters**: `id, name, traits(json), relationships(json), speech_style, history(json)`
- **events**: `id, order_index, summary, characters_involved(json), world_refs(json), created_at`
- **per_child** *(schema only — not populated, no logic)*: `child_id, characters_met(json), threads(json)`

## Storage interface

`WorldStore` keeps signatures clean and swappable; `SqliteWorldStore` is the
SQLite implementation.

```python
from worldstate import SqliteWorldStore

store = SqliteWorldStore.open("emberfall.db")   # or ":memory:"

store.add_canon("Lanterns never gutter.", category="setting", immutable=True)
pip = store.add_character("Pip the Fox", traits=["curious"],
                          relationships={"hollow": "home"}, speech_style="warm")
store.write_events([
    {"order_index": 1, "summary": "Pip lights the first lantern.",
     "characters_involved": [pip.id], "world_refs": ["ever-lantern"]},
])

slice = store.get_world_slice(character_ids=[pip.id], recent_events=5,
                              canon_categories=["setting", "tone"])
# -> {"canon": [...], "characters": [...], "events": [...]}  (JSON-serializable)
```

Required functions: `get_world_slice(character_ids=None, recent_events=N,
canon_categories=None)`, `write_events(events)`, `get_character(id)`,
`add_character(...)`, `add_canon(...)` (plus `get_canon`, `list_canon`,
`list_characters`).

## Run

```bash
python -m pytest              # 23 tests
python scripts/seed_demo.py   # end-to-end demo
```
