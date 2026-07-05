#!/usr/bin/env python3
"""Demo: exercise the world-state backbone end to end.

Creates a world, applies an approved changeset that seeds canon, retrieves the
full world state, then applies a second changeset that evolves the world, and
prints the result. No generation/validation/personalization — just the backbone.

Run:  python scripts/seed_demo.py [path-to-db]   (defaults to in-memory)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from worldstate import WorldStateStore  # noqa: E402


def seed(store: WorldStateStore, world_id: int) -> None:
    cs = store.propose_changeset(world_id, author="demo", note="Seed Emberfall canon.")
    store.stage_entity(cs.id, kind="character", slug="pip", name="Pip the Fox",
                       summary="A curious young fox who lights the lanterns at dusk.")
    store.stage_entity(cs.id, kind="location", slug="hollow", name="The Whispering Hollow",
                       summary="A cosy den beneath the old oak.")
    store.stage_entity(cs.id, kind="item", slug="ever-lantern", name="The Ever-Lantern",
                       summary="A lantern whose flame never gutters.")
    store.stage_fact(cs.id, entity_slug="pip", key="species", value="fox")
    store.stage_fact(cs.id, entity_slug="pip", key="bravery", value="growing")
    store.stage_relationship(cs.id, src_slug="pip", dst_slug="hollow", kind="lives_in",
                             detail="under the old oak")
    store.stage_relationship(cs.id, src_slug="pip", dst_slug="ever-lantern", kind="keeper_of")
    store.stage_event(cs.id, seq=1, title="Pip lights the first lantern",
                      summary="Dusk falls and Pip carries the Ever-Lantern to the ridge.",
                      participants=[{"entity_slug": "pip", "role": "protagonist"}])
    store.approve_changeset(cs.id)
    store.apply_changeset(cs.id)


def evolve(store: WorldStateStore, world_id: int) -> None:
    cs = store.propose_changeset(world_id, author="demo", note="Pip grows braver.")
    store.stage_fact_update(cs.id, entity_slug="pip", key="bravery", value="bold")
    store.stage_event(cs.id, seq=2, title="Pip explores beyond the Hollow",
                      participants=[{"entity_slug": "pip", "role": "protagonist"}])
    store.approve_changeset(cs.id)
    store.apply_changeset(cs.id)


def dump(store: WorldStateStore, world_id: int) -> None:
    state = store.retrieve_world_state(world_id)
    print(f"World: {state.world.name} ({state.world.slug})")
    print(f"  entities: {len(state.entities)}  facts: {len(state.facts)}  "
          f"relationships: {len(state.relationships)}  events: {len(state.events)}")
    for e in state.entities:
        facts = ", ".join(f"{f.key}={f.value}" for f in state.facts_for(e.id))
        prov = f"[created by cs#{e.created_by_changeset_id}, updated by cs#{e.updated_by_changeset_id}]"
        print(f"  - {e.kind:<9} {e.slug:<13} {e.name}")
        if facts:
            print(f"      facts: {facts}  {prov}")
    for r in state.relationships:
        src = next(e for e in state.entities if e.id == r.src_entity_id)
        dst = next(e for e in state.entities if e.id == r.dst_entity_id)
        print(f"  * {src.slug} --{r.kind}--> {dst.slug}"
              + (f" ({r.detail})" if r.detail else ""))
    for ev in state.events:
        who = [p for p in state.event_participants if p.event_id == ev.id]
        roles = ", ".join(f"{store_entity_slug(state, p.entity_id)}:{p.role}" for p in who)
        print(f"  @ t{ev.seq}: {ev.title}" + (f" [{roles}]" if roles else ""))


def store_entity_slug(state, entity_id: int) -> str:
    for e in state.entities:
        if e.id == entity_id:
            return e.slug
    return str(entity_id)


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else ":memory:"
    store = WorldStateStore.open(path)
    try:
        world = store.create_world("emberfall", "Emberfall",
                                   "A persistent bedtime world of lanternlight.")
        seed(store, world.id)
        print("== After seeding ==")
        dump(store, world.id)
        evolve(store, world.id)
        print("\n== After evolving (Pip grows braver, a new event) ==")
        dump(store, world.id)
        print(f"\nChangesets applied: {len(store.list_changesets(world.id))}")
    finally:
        store.close()


if __name__ == "__main__":
    main()
