"""Result types for Stage 1 generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GenerationResult:
    """One generated story plus provenance of what it was built from.

    - ``canon_used`` / ``characters_used``: ids the MODEL reported drawing on
      (a subset of what it was given).
    - ``provided``: the FULL world slice that was retrieved and sent to the
      model — the ground truth a later validator can check ``*_used`` against.
    """

    story: str
    canon_used: list[int]
    characters_used: list[int]
    provided: dict
    model: str
    usage: Optional[dict] = None

    # -- convenience views over the provided slice ---------------------------

    def used_canon_statements(self) -> list[str]:
        by_id = {c["id"]: c["statement"] for c in self.provided.get("canon", [])}
        return [by_id[i] for i in self.canon_used if i in by_id]

    def used_character_names(self) -> list[str]:
        by_id = {c["id"]: c["name"] for c in self.provided.get("characters", [])}
        return [by_id[i] for i in self.characters_used if i in by_id]

    def provided_canon_ids(self) -> list[int]:
        return [c["id"] for c in self.provided.get("canon", [])]

    def provided_character_ids(self) -> list[int]:
        return [c["id"] for c in self.provided.get("characters", [])]
