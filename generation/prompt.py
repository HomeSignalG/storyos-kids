"""Render a retrieved world slice into the prompt.

Each canon fact and character is labelled with its id so the model can report
back which ones it used. IMMUTABLE canon is flagged explicitly.
"""

from __future__ import annotations

from .config import GenerationConfig


def _canon_block(canon: list[dict]) -> str:
    if not canon:
        return "(none)"
    lines = []
    for c in canon:
        flag = " (IMMUTABLE)" if c.get("immutable") else ""
        lines.append(f"[canon:{c['id']}]{flag} ({c['category']}) {c['statement']}")
    return "\n".join(lines)


def _characters_block(characters: list[dict]) -> str:
    if not characters:
        return "(none)"
    lines = []
    for ch in characters:
        traits = ", ".join(ch.get("traits") or []) or "—"
        rels = ch.get("relationships") or {}
        rel_str = ", ".join(f"{k}: {v}" for k, v in rels.items()) or "—"
        history = "; ".join(ch.get("history") or []) or "—"
        lines.append(
            f"[character:{ch['id']}] {ch['name']}\n"
            f"    traits: {traits}\n"
            f"    speech_style: {ch.get('speech_style') or '—'}\n"
            f"    relationships: {rel_str}\n"
            f"    history: {history}"
        )
    return "\n".join(lines)


def _events_block(events: list[dict]) -> str:
    if not events:
        return "(none)"
    lines = []
    for e in events:
        who = ", ".join(str(i) for i in (e.get("characters_involved") or [])) or "—"
        refs = ", ".join(e.get("world_refs") or []) or "—"
        lines.append(
            f"[t{e['order_index']}] {e['summary']}  (characters: {who}; refs: {refs})"
        )
    return "\n".join(lines)


def render_prompt(world_slice: dict, config: GenerationConfig) -> tuple[str, str]:
    """Return (system, user) prompt strings for a world slice."""
    user = (
        config.user_template
        .replace("{{canon}}", _canon_block(world_slice.get("canon", [])))
        .replace("{{characters}}", _characters_block(world_slice.get("characters", [])))
        .replace("{{recent_events}}", _events_block(world_slice.get("events", [])))
        .strip()
    )
    return config.system, user
