"""Load the Stage 1 generation config (model + prompt template) from TOML.

Read via the stdlib ``tomllib`` — no third-party dependency. The prompt text
lives in ``config/generation.toml``, never in source.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Union

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "generation.toml"

_REQUIRED = ("model", "effort", "max_tokens", "system", "user_template")


@dataclass(frozen=True)
class GenerationConfig:
    model: str
    effort: str
    max_tokens: int
    system: str
    user_template: str


def load_config(path: Union[str, Path, None] = None) -> GenerationConfig:
    p = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    with open(p, "rb") as f:
        data = tomllib.load(f)
    missing = [k for k in _REQUIRED if k not in data]
    if missing:
        raise ValueError(f"{p}: missing config keys: {', '.join(missing)}")
    return GenerationConfig(
        model=data["model"],
        effort=data["effort"],
        max_tokens=int(data["max_tokens"]),
        system=data["system"].strip(),
        user_template=data["user_template"],
    )
