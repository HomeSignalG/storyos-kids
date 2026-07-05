#!/usr/bin/env python3
"""Demo: exercise the world-state backbone end to end.

Seeds canon + characters + events, then prints a world slice via
get_world_slice(). No generation/validation/personalization — just the
backbone. The per_child table is created by the schema but left empty.

Run:  python scripts/seed_demo.py [path-to-db]   (defaults to in-memory)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from worldstate import SqliteWorldStore  # noqa: E402


def seed(store: SqliteWorldStore) -> dict:
    store.add_canon("Emberfall is lit by lanterns that never gutter.",
                    category="setting", immutable=True)
    store.add_canon("Night falls gently; nothing truly frightening happens.",
                    category="tone", immutable=True)
    store.add_canon("The old oak marks the centre of the Whispering Hollow.",
                    category="geography")
    store.add_canon("Every creature keeps at least one small promise a day.",
                    category="lore")
    store.add_canon("The Ever-Lantern always guides a lost traveller home by morning.",
                    category="lore", immutable=True)

    pip = store.add_character(
        "Pip the Fox",
        traits=["curious", "kind", "growing braver"],
        relationships={"hollow": "home", "ever-lantern": "keeper"},
        speech_style="warm, inquisitive, lots of questions",
        history=["Found the Ever-Lantern at the ridge."],
    )
    bramble = store.add_character(
        "Bramble the Hedgehog",
        traits=["cautious", "loyal"],
        relationships={"pip": "best friend"},
        speech_style="slow and careful",
    )

    store.write_events([
        {"order_index": 1, "summary": "Pip lights the first lantern at dusk.",
         "characters_involved": [pip.id], "world_refs": ["ever-lantern"]},
        {"order_index": 2, "summary": "Pip and Bramble explore beyond the Hollow.",
         "characters_involved": [pip.id, bramble.id], "world_refs": ["hollow"]},
        {"order_index": 3, "summary": "They find a quiet glade of glowing moss.",
         "characters_involved": [pip.id, bramble.id], "world_refs": []},
    ])
    return {"pip": pip.id, "bramble": bramble.id}


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else ":memory:"
    store = SqliteWorldStore.open(path)
    try:
        ids = seed(store)

        print("== Full world slice ==")
        full = store.get_world_slice()
        print(json.dumps(full, indent=2))

        print("\n== Focused slice: Pip only, 2 most recent events, tone+setting canon ==")
        focused = store.get_world_slice(
            character_ids=[ids["pip"]],
            recent_events=2,
            canon_categories=["tone", "setting"],
        )
        print(json.dumps(focused, indent=2))

        per_child = store.conn.execute("SELECT COUNT(*) FROM per_child").fetchone()[0]
        print(f"\nper_child rows: {per_child}  (schema-only stub, intentionally empty)")
    finally:
        store.close()


if __name__ == "__main__":
    main()
