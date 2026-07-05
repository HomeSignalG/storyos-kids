"""World-State Backbone — the persistent canon layer for storyos-kids.

The world is a database; canon is truth. This package provides the schema,
read models, and the changeset-based write path. It does NOT generate,
validate, or personalize stories — see docs/CURRENT_TASK.md.
"""

from .models import (
    Change,
    Changeset,
    Entity,
    Event,
    EventParticipant,
    Fact,
    Relationship,
    World,
    WorldState,
)
from .repository import (
    InvalidStateError,
    NotFoundError,
    WorldStateError,
    WorldStateStore,
)

__all__ = [
    "WorldStateStore",
    "WorldStateError",
    "NotFoundError",
    "InvalidStateError",
    "World",
    "Entity",
    "Fact",
    "Relationship",
    "Event",
    "EventParticipant",
    "Changeset",
    "Change",
    "WorldState",
]
