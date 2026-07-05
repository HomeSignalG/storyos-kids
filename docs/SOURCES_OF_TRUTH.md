# SOURCES OF TRUTH — Decided Facts
# Settled. Do not relitigate or contradict. To change one, STOP and ask.

## Product
- Vertical: kids bedtime stories. Persistent, coherent, evolving worlds.
- Personalization is TASTE-AND-WORLD, not name-insertion. The child is NOT necessarily the hero.
- Structure: a few deep SHARED signature worlds (brand layer) + per-child adaptation on top (moat layer).
- Fewer, deeper, shared worlds beat infinite shallow personal ones.

## The moat
- The world-coherence engine (keeping AI faithful to canon across unlimited generation).
- Structure-labeled behavioral outcome data (what the child does, mapped to story structure).
- Persistent-world attachment (switching cost).
- The story generator itself is a COMMODITY. Invest in coherence + data, not the generator.

## Core architecture (decided)
- The world is a DATABASE. The AI is a RENDERER. Canon is truth; prose is a view.
- Generation loop (LATER, not now): retrieve -> constrain -> validate -> write back.
- Coherence comes from ENFORCEMENT (a validation gate), not from hoping the model complies.
- Batch-ahead-with-audit: stories generated in advance, audited before delivery. (LATER.)
- Three gates before a story reaches a child: automated validation -> optional human review -> parent approval. (LATER.)

## Economics (decided constraints)
- TTS: RENT now (e.g. ElevenLabs). Self-host open TTS only later at scale. NEVER build a voice model.
- Governing metric is cost-per-listening-hour, not cost-per-story.
- "Unlimited" is dangerous. Do not design for literal unlimited generation.
- Consider text-first for V1. Flag as open question; don't assume.

## Compliance (hard constraints, kids vertical)
- COPPA / UK Age-Appropriate Design Code apply. Parent-in-the-loop is core.
- Learn STORY TASTE, not regulated behavioral profiles of the child.
- Content genuinely age-appropriate. Own guardrails strong regardless of parent gate.
- Secrets never in code/config/commits.

## Explicitly OUT of scope right now
- No recommendation engine, referral system, community, subscription platform.
- No multi-world support (one signature world first).
- No real-time personalization (pre-built spine first).
- No self-hosted TTS or self-hosted models.
- No merchandise/IP build-out.
- No UI beyond what a task explicitly requires.

## Current phase
- Building the WORLD-STATE BACKBONE only. See /docs/CURRENT_TASK.md.
- Not building: generation, validator
