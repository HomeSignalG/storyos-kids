# storyos-kids — World-State Backbone

Persistent canon layer for coherent, evolving kids' bedtime story worlds.

> The world is a **database**. The AI is a **renderer**. Canon is truth.
> See [`docs/SOURCES_OF_TRUTH.md`](docs/SOURCES_OF_TRUTH.md) and
> [`docs/CURRENT_TASK.md`](docs/CURRENT_TASK.md).

This repository currently contains **only** the world-state backbone: the
schema, read models, and the changeset-based write path. No generation,
validation, or personalization yet.

## Layout

```
worldstate/
  schema.sql       SQLite schema (canon + changeset audit trail)
  db.py            connection + schema init
  models.py        dataclasses returned by reads
  repository.py    WorldStateStore: reads canon, writes via changesets
scripts/
  seed_demo.py     end-to-end demonstration
tests/             pytest suite
```

## The one write path

Canon never changes by direct edit. The only way in is an approved changeset:

```python
from worldstate import WorldStateStore

store = WorldStateStore.open("emberfall.db")   # or ":memory:"
world = store.create_world("emberfall", "Emberfall")

cs = store.propose_changeset(world.id, author="me", note="seed")
store.stage_entity(cs.id, kind="character", slug="pip", name="Pip the Fox")
store.stage_fact(cs.id, entity_slug="pip", key="species", value="fox")
store.approve_changeset(cs.id)     # gate
store.apply_changeset(cs.id)       # atomic write-back, stamps provenance

state = store.retrieve_world_state(world.id)   # the "retrieve" step
```

Applying a changeset is atomic: if any change fails, none are written and the
changeset stays `approved` (not `applied`). Every canon row records the
changeset that created and last modified it.

## Run

```bash
python -m pytest         # test suite
python scripts/seed_demo.py
```
