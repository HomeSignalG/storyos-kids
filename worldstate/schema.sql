-- World-State Backbone schema (SQLite).
-- Canon is truth. Every canon row is created/mutated ONLY by applying an
-- approved changeset, and carries provenance back to that changeset.

PRAGMA foreign_keys = ON;

-- Schema version marker, for future migrations.
CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- Write-back audit trail: changesets and their individual changes.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS changesets (
    id          INTEGER PRIMARY KEY,
    world_id    INTEGER NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    status      TEXT NOT NULL DEFAULT 'proposed'
                    CHECK (status IN ('proposed', 'approved', 'applied', 'rejected')),
    author      TEXT NOT NULL DEFAULT '',
    note        TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL,
    approved_at TEXT,
    applied_at  TEXT
);

CREATE TABLE IF NOT EXISTS changes (
    id            INTEGER PRIMARY KEY,
    changeset_id  INTEGER NOT NULL REFERENCES changesets(id) ON DELETE CASCADE,
    seq           INTEGER NOT NULL,
    op            TEXT NOT NULL CHECK (op IN ('insert', 'update', 'delete')),
    target_table  TEXT NOT NULL
                      CHECK (target_table IN ('entities', 'facts', 'relationships',
                                              'events', 'event_participants')),
    target_id     INTEGER,          -- resolved row id (set for update/delete; stamped after insert)
    payload       TEXT NOT NULL DEFAULT '{}',  -- JSON describing the mutation
    UNIQUE (changeset_id, seq)
);

-- ---------------------------------------------------------------------------
-- Canon: the world and everything in it.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS worlds (
    id          INTEGER PRIMARY KEY,
    slug        TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS entities (
    id                       INTEGER PRIMARY KEY,
    world_id                 INTEGER NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    kind                     TEXT NOT NULL
                                 CHECK (kind IN ('character', 'location', 'item',
                                                 'faction', 'concept')),
    slug                     TEXT NOT NULL,
    name                     TEXT NOT NULL,
    summary                  TEXT NOT NULL DEFAULT '',
    status                   TEXT NOT NULL DEFAULT 'active'
                                 CHECK (status IN ('active', 'archived')),
    created_by_changeset_id  INTEGER REFERENCES changesets(id) ON DELETE SET NULL,
    updated_by_changeset_id  INTEGER REFERENCES changesets(id) ON DELETE SET NULL,
    created_at               TEXT NOT NULL,
    updated_at               TEXT NOT NULL,
    UNIQUE (world_id, slug)
);

CREATE TABLE IF NOT EXISTS facts (
    id                       INTEGER PRIMARY KEY,
    world_id                 INTEGER NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    entity_id                INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    key                      TEXT NOT NULL,
    value                    TEXT NOT NULL DEFAULT '',
    created_by_changeset_id  INTEGER REFERENCES changesets(id) ON DELETE SET NULL,
    updated_by_changeset_id  INTEGER REFERENCES changesets(id) ON DELETE SET NULL,
    created_at               TEXT NOT NULL,
    updated_at               TEXT NOT NULL,
    UNIQUE (entity_id, key)
);

CREATE TABLE IF NOT EXISTS relationships (
    id                       INTEGER PRIMARY KEY,
    world_id                 INTEGER NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    src_entity_id            INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    dst_entity_id            INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    kind                     TEXT NOT NULL,
    detail                   TEXT NOT NULL DEFAULT '',
    created_by_changeset_id  INTEGER REFERENCES changesets(id) ON DELETE SET NULL,
    updated_by_changeset_id  INTEGER REFERENCES changesets(id) ON DELETE SET NULL,
    created_at               TEXT NOT NULL,
    updated_at               TEXT NOT NULL,
    UNIQUE (src_entity_id, dst_entity_id, kind)
);

CREATE TABLE IF NOT EXISTS events (
    id                       INTEGER PRIMARY KEY,
    world_id                 INTEGER NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
    seq                      INTEGER NOT NULL,
    title                    TEXT NOT NULL,
    summary                  TEXT NOT NULL DEFAULT '',
    created_by_changeset_id  INTEGER REFERENCES changesets(id) ON DELETE SET NULL,
    created_at               TEXT NOT NULL,
    UNIQUE (world_id, seq)
);

CREATE TABLE IF NOT EXISTS event_participants (
    id         INTEGER PRIMARY KEY,
    event_id   INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    entity_id  INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    role       TEXT NOT NULL DEFAULT '',
    UNIQUE (event_id, entity_id, role)
);

CREATE INDEX IF NOT EXISTS idx_entities_world   ON entities(world_id);
CREATE INDEX IF NOT EXISTS idx_facts_entity     ON facts(entity_id);
CREATE INDEX IF NOT EXISTS idx_rel_src          ON relationships(src_entity_id);
CREATE INDEX IF NOT EXISTS idx_rel_dst          ON relationships(dst_entity_id);
CREATE INDEX IF NOT EXISTS idx_events_world     ON events(world_id);
CREATE INDEX IF NOT EXISTS idx_changes_cs       ON changes(changeset_id);
CREATE INDEX IF NOT EXISTS idx_changesets_world ON changesets(world_id);
