-- World-State Backbone schema (SQLite).
-- Exact tables/fields per docs/CURRENT_TASK.md. Backbone only: no generation,
-- validation, or personalization. `per_child` is a schema-only stub for later.
--
-- JSON-typed fields are stored as TEXT holding a JSON document.
-- Booleans are stored as INTEGER 0/1 (SQLite has no native boolean).

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS canon (
    id        INTEGER PRIMARY KEY,
    statement TEXT NOT NULL,
    category  TEXT NOT NULL,
    immutable INTEGER NOT NULL DEFAULT 0   -- bool (0/1)
);

CREATE TABLE IF NOT EXISTS characters (
    id            INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,
    traits        TEXT NOT NULL DEFAULT '[]',   -- json
    relationships TEXT NOT NULL DEFAULT '{}',   -- json
    speech_style  TEXT NOT NULL DEFAULT '',
    history       TEXT NOT NULL DEFAULT '[]'    -- json
);

CREATE TABLE IF NOT EXISTS events (
    id                  INTEGER PRIMARY KEY,
    order_index         INTEGER NOT NULL,
    summary             TEXT NOT NULL,
    characters_involved TEXT NOT NULL DEFAULT '[]',  -- json
    world_refs          TEXT NOT NULL DEFAULT '[]',  -- json
    created_at          TEXT NOT NULL
);

-- SCHEMA ONLY. Not populated by any function; no personalization logic here.
CREATE TABLE IF NOT EXISTS per_child (
    child_id       TEXT PRIMARY KEY,
    characters_met TEXT NOT NULL DEFAULT '[]',  -- json
    threads        TEXT NOT NULL DEFAULT '[]'   -- json
);

CREATE INDEX IF NOT EXISTS idx_canon_category  ON canon(category);
CREATE INDEX IF NOT EXISTS idx_events_order     ON events(order_index);
