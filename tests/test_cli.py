import json

import pytest

from worldstate import WorldStateStore
from worldstate.cli import main


@pytest.fixture()
def seeded_db(tmp_path):
    path = tmp_path / "w.db"
    store = WorldStateStore.open(path)
    world = store.create_world("emberfall", "Emberfall")
    cs = store.propose_changeset(world.id, author="t")
    store.stage_entity(cs.id, kind="character", slug="pip", name="Pip")
    store.stage_fact(cs.id, entity_slug="pip", key="species", value="fox")
    store.stage_event(cs.id, seq=1, title="First light")
    store.approve_changeset(cs.id)
    store.apply_changeset(cs.id)
    store.close()
    return str(path)


def test_cli_worlds(seeded_db, capsys):
    main(["worlds", seeded_db])
    out = capsys.readouterr().out
    assert "emberfall" in out


def test_cli_show(seeded_db, capsys):
    main(["show", seeded_db, "emberfall"])
    out = capsys.readouterr().out
    assert "Pip" in out
    assert "species=fox" in out
    assert "t1: First light" in out


def test_cli_log(seeded_db, capsys):
    main(["log", seeded_db, "emberfall"])
    out = capsys.readouterr().out
    assert "insert" in out and "entities" in out


def test_cli_export_is_json(seeded_db, capsys):
    main(["export", seeded_db, "emberfall"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["world"]["slug"] == "emberfall"


def test_cli_unknown_world_exits(seeded_db):
    with pytest.raises(SystemExit) as exc:
        main(["show", seeded_db, "nope"])
    assert exc.value.code == 2
