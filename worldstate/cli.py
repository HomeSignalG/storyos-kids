"""Read-only inspection CLI for a world-state database.

Dev tooling for the backbone — it inspects and exports; it does NOT generate,
validate, or personalize. Writes still go only through the changeset API.

    python -m worldstate init    <db>
    python -m worldstate worlds  <db>
    python -m worldstate show     <db> <world-slug>
    python -m worldstate log      <db> <world-slug>
    python -m worldstate export    <db> <world-slug>
"""

from __future__ import annotations

import argparse
import json
import sys

from .repository import NotFoundError, WorldStateStore


def _resolve_world(store: WorldStateStore, slug: str):
    try:
        return store.get_world_by_slug(slug)
    except NotFoundError:
        print(f"error: no world with slug {slug!r}", file=sys.stderr)
        raise SystemExit(2)


def cmd_init(store: WorldStateStore, args) -> None:
    print(f"initialized world-state db at {args.db} (schema present)")


def cmd_worlds(store: WorldStateStore, args) -> None:
    worlds = store.list_worlds()
    if not worlds:
        print("(no worlds)")
        return
    for w in worlds:
        print(f"{w.id}\t{w.slug}\t{w.name}")


def cmd_show(store: WorldStateStore, args) -> None:
    world = _resolve_world(store, args.slug)
    state = store.retrieve_world_state(world.id)
    print(f"World: {state.world.name} ({state.world.slug})")
    print(f"  entities={len(state.entities)} facts={len(state.facts)} "
          f"relationships={len(state.relationships)} events={len(state.events)}")
    for e in state.entities:
        facts = ", ".join(f"{f.key}={f.value}" for f in state.facts_for(e.id))
        print(f"  - {e.kind:<9} {e.slug:<14} {e.name}"
              + (f"  [{facts}]" if facts else ""))
    for r in state.relationships:
        by_id = {e.id: e.slug for e in state.entities}
        print(f"  * {by_id.get(r.src_entity_id)} --{r.kind}--> {by_id.get(r.dst_entity_id)}")
    for ev in state.events:
        print(f"  @ t{ev.seq}: {ev.title}")


def cmd_log(store: WorldStateStore, args) -> None:
    world = _resolve_world(store, args.slug)
    for row in store.audit_log(world.id):
        print(f"cs#{row['changeset_id']}/{row['seq']}\t{row['op']}\t"
              f"{row['target_table']}#{row['target_id']}\t{json.dumps(row['payload'])}")


def cmd_export(store: WorldStateStore, args) -> None:
    world = _resolve_world(store, args.slug)
    print(json.dumps(store.export_world(world.id), indent=2))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="worldstate", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    for name, help_text in [
        ("init", "create/open a db (ensures schema)"),
        ("worlds", "list worlds"),
    ]:
        sp = sub.add_parser(name, help=help_text)
        sp.add_argument("db")
    for name, help_text in [
        ("show", "print a world's canon"),
        ("log", "print a world's applied-change audit log"),
        ("export", "print a world's canon as JSON"),
    ]:
        sp = sub.add_parser(name, help=help_text)
        sp.add_argument("db")
        sp.add_argument("slug")
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    handler = {
        "init": cmd_init,
        "worlds": cmd_worlds,
        "show": cmd_show,
        "log": cmd_log,
        "export": cmd_export,
    }[args.command]
    store = WorldStateStore.open(args.db)
    try:
        handler(store, args)
    finally:
        store.close()


if __name__ == "__main__":
    main()
