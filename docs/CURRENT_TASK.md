# CURRENT TASK — Stage 1: Constrained Generation (READ-ONLY from the backbone)

## Goal
Generate ONE short kids' bedtime story that is faithful to the world state held
in the backbone. Generation READS FROM the backbone via `get_world_slice`; it
does not write anything back and does not validate. This is the "retrieve ->
constrain -> generate" slice of the eventual loop — NO validate, NO write-back.

## Must do
1. Call `get_world_slice(character_ids, recent_events, canon_categories)` to
   retrieve the relevant characters, canon, and recent events.
2. Generate ONE short story (a few hundred words) that:
   - Obeys the retrieved canon, especially rules marked `immutable`.
   - Continues from the recent events (respects the timeline).
   - Keeps characters in voice (uses their traits + speech_style).
3. Use the Anthropic API. The prompt lives in a config/template file, never
   hard-coded in source. API key is provided via environment (ANTHROPIC_API_KEY).
4. Output the story PLUS a structured record of which canon facts (by id) and
   characters (by id) it used.

## Explicitly NOT in this task
- NO validator / canon-adherence checker (that is a later stage).
- NO write-back to the world state (canon, characters, events, per_child all
  untouched). Generation is read-only against the backbone.
- No personalization, no per_child usage, no TTS, no UI.

## Constraints (from SOURCES_OF_TRUTH)
- The story generator is a commodity; keep it swappable and thin.
- Prompt/config in a file, not in code. Secrets only via environment.
- Model: latest capable Claude by default; configurable.

## Stop condition
A generation module + the prompt/config file + a demo that seeds a world,
retrieves a slice, and generates ONE story, printing the story and the
structured usage record; tests (Anthropic API mocked) green; committed and
pushed. Halt with the generated story shown for review.
