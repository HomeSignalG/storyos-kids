"""Stage 1: constrained generation that READS FROM the backbone.

Retrieve a world slice -> render the prompt -> one Anthropic Messages API call
with structured output -> return the story plus what it drew on. Read-only: this
module never writes back to the world state and does not validate canon
adherence (that is a later stage).
"""

from __future__ import annotations

import json
from typing import Optional

from worldstate.store import WorldStore

from .config import GenerationConfig, load_config
from .models import GenerationResult
from .prompt import render_prompt

# Structured-output schema: the model returns the story plus the ids it used.
STORY_SCHEMA = {
    "type": "object",
    "properties": {
        "story": {"type": "string"},
        "canon_used": {"type": "array", "items": {"type": "integer"}},
        "characters_used": {"type": "array", "items": {"type": "integer"}},
    },
    "required": ["story", "canon_used", "characters_used"],
    "additionalProperties": False,
}


class GenerationError(RuntimeError):
    pass


def _default_client():
    import anthropic  # lazy: tests inject a client and need neither SDK nor key

    return anthropic.Anthropic()


def _extract_json(response) -> dict:
    if getattr(response, "stop_reason", None) == "refusal":
        raise GenerationError("model refused to generate")
    text = next((b.text for b in response.content if getattr(b, "type", None) == "text"), None)
    if text is None:
        raise GenerationError("no text block in response")
    return json.loads(text)


def generate_story(
    store: WorldStore,
    *,
    character_ids: Optional[list] = None,
    recent_events: Optional[int] = 5,
    canon_categories: Optional[list] = None,
    config: Optional[GenerationConfig] = None,
    client=None,
) -> GenerationResult:
    """Generate ONE story constrained by the retrieved world slice."""
    cfg = config or load_config()
    world_slice = store.get_world_slice(
        character_ids=character_ids,
        recent_events=recent_events,
        canon_categories=canon_categories,
    )
    system, user = render_prompt(world_slice, cfg)

    client = client or _default_client()
    response = client.messages.create(
        model=cfg.model,
        max_tokens=cfg.max_tokens,
        thinking={"type": "adaptive"},
        output_config={
            "effort": cfg.effort,
            "format": {"type": "json_schema", "schema": STORY_SCHEMA},
        },
        system=system,
        messages=[{"role": "user", "content": user}],
    )

    data = _extract_json(response)
    usage = None
    if getattr(response, "usage", None) is not None:
        u = response.usage
        usage = {
            "input_tokens": getattr(u, "input_tokens", None),
            "output_tokens": getattr(u, "output_tokens", None),
        }

    return GenerationResult(
        story=data["story"],
        canon_used=data["canon_used"],
        characters_used=data["characters_used"],
        provided=world_slice,
        model=getattr(response, "model", cfg.model),
        usage=usage,
    )
