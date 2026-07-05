"""World-State Backbone — the persistent canon layer for storyos-kids.

The world is a database; canon is truth. This package provides the schema,
read models, and a swappable storage interface. It does NOT generate,
validate, or personalize stories — see docs/CURRENT_TASK.md.
"""

from .models import Canon, Character, Event, PerChild
from .store import NotFoundError, SqliteWorldStore, WorldStore

__all__ = [
    "WorldStore",
    "SqliteWorldStore",
    "NotFoundError",
    "Canon",
    "Character",
    "Event",
    "PerChild",
]
