"""Stage 1 constrained generation for storyos-kids.

Reads a world slice from the backbone and generates ONE story faithful to
canon. Read-only against the world state; no validation, no write-back.
See docs/CURRENT_TASK.md.
"""

from .config import GenerationConfig, load_config
from .generate import GenerationError, generate_story
from .models import GenerationResult
from .prompt import render_prompt

__all__ = [
    "generate_story",
    "GenerationError",
    "GenerationResult",
    "GenerationConfig",
    "load_config",
    "render_prompt",
]
