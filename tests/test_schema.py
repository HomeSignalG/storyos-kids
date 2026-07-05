import sqlite3

from worldstate import db


EXPECTED_COLUMNS = {
    "canon": ["id", "statement", "category", "immutable"],
    "characters": ["id", "name", "traits", "relationships", "speech_style", "history"],
    "events": ["id", "order_index", "summary", "characters_involved",
               "world_refs", "created_at"],
    "per_child": ["child_id", "characters_met", "threads"],
}


def _columns(conn, table):
    return [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def test_tables_exist_with_exact_columns():
    conn = db.connect(":memory:")
    tables = {
        r["name"]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    for table, cols in EXPECTED_COLUMNS.items():
        assert table in tables, f"missing table {table}"
        assert _columns(conn, table) == cols, f"columns mismatch for {table}"
    conn.close()


def test_no_unexpected_domain_tables():
    conn = db.connect(":memory:")
    tables = {
        r["name"]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    }
    assert tables == set(EXPECTED_COLUMNS), tables
    conn.close()


def test_per_child_schema_only_but_usable():
    # No function populates per_child, but the schema must accept its exact shape.
    conn = db.connect(":memory:")
    assert conn.execute("SELECT COUNT(*) FROM per_child").fetchone()[0] == 0
    conn.execute(
        "INSERT INTO per_child(child_id, characters_met, threads) VALUES (?, ?, ?)",
        ("child-123", "[1,2]", "[]"),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM per_child").fetchone()
    assert row["child_id"] == "child-123"
    conn.close()
