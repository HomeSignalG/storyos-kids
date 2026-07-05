#!/usr/bin/env python3
"""Stage 1 demo: seed a world, retrieve a slice, generate ONE story.

Reads from the backbone and calls the Anthropic API (needs ANTHROPIC_API_KEY in
the environment). Prints the story plus the structured usage record. Does NOT
write anything back to the world state.

Run:  ANTHROPIC_API_KEY=... python scripts/generate_demo.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from worldstate import SqliteWorldStore                          # noqa: E402
from generation import generate_story, load_config, render_prompt  # noqa: E402


def seed(store: SqliteWorldStore) -> dict:
    store.add_canon("Emberfall is lit by lanterns that never gutter.",
                    category="setting", immutable=True)
    store.add_canon("Night falls gently; nothing truly frightening happens.",
                    category="tone", immutable=True)
    store.add_canon("The old oak marks the centre of the Whispering Hollow.",
                    category="geography")
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
    ])
    return {"pip": pip.id, "bramble": bramble.id}


def dry_run(store: SqliteWorldStore, character_ids: list) -> None:
    """No API call: print the exact prompt that WOULD be sent to the model."""
    cfg = load_config()
    world_slice = store.get_world_slice(character_ids=character_ids, recent_events=5)
    system, user = render_prompt(world_slice, cfg)
    print("=" * 70)
    print(f"DRY RUN — no ANTHROPIC_API_KEY set; model={cfg.model} not called")
    print("=" * 70)
    print("SYSTEM PROMPT:\n")
    print(system)
    print("\nUSER PROMPT (rendered from the retrieved world slice):\n")
    print(user)
    print("\n(Set ANTHROPIC_API_KEY and re-run to generate a real story.)")


def main() -> None:
    store = SqliteWorldStore.open(":memory:")
    try:
        ids = seed(store)
        character_ids = [ids["pip"], ids["bramble"]]

        if "--dry-run" in sys.argv or not os.environ.get("ANTHROPIC_API_KEY"):
            dry_run(store, character_ids)
            return

        result = generate_story(store, character_ids=character_ids, recent_events=5)

        print("=" * 70)
        print("STORY")
        print("=" * 70)
        print(result.story.strip())
        print()
        print("=" * 70)
        print("STRUCTURED RECORD")
        print("=" * 70)
        print(f"model: {result.model}")
        if result.usage:
            print(f"usage: {result.usage}")
        print(f"\ncanon PROVIDED (ids): {result.provided_canon_ids()}")
        print(f"canon USED   (ids): {result.canon_used}")
        for s in result.used_canon_statements():
            print(f"   - {s}")
        print(f"\ncharacters PROVIDED (ids): {result.provided_character_ids()}")
        print(f"characters USED   (ids): {result.characters_used}  "
              f"{result.used_character_names()}")

        # Prove read-only: the world state is unchanged after generation.
        after = store.get_world_slice()
        print(f"\n(read-only check) canon rows still: {len(after['canon'])}, "
              f"characters: {len(after['characters'])}, events: {len(after['events'])}")
    finally:
        store.close()


if __name__ == "__main__":
    main()
