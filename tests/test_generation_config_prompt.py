import textwrap

import pytest

from generation import load_config, render_prompt


def test_load_default_config():
    cfg = load_config()
    assert cfg.model  # non-empty
    assert cfg.effort in ("low", "medium", "high", "xhigh", "max")
    assert cfg.max_tokens > 0
    assert "storyteller" in cfg.system.lower()
    assert "{{canon}}" in cfg.user_template


def test_load_config_missing_key(tmp_path):
    p = tmp_path / "bad.toml"
    p.write_text('model = "x"\n')  # missing the rest
    with pytest.raises(ValueError):
        load_config(p)


def test_load_config_roundtrip(tmp_path):
    p = tmp_path / "gen.toml"
    p.write_text(textwrap.dedent('''
        model = "claude-sonnet-5"
        effort = "medium"
        max_tokens = 1234
        system = "Sys."
        user_template = "{{canon}} {{characters}} {{recent_events}}"
    '''))
    cfg = load_config(p)
    assert cfg.model == "claude-sonnet-5"
    assert cfg.effort == "medium"
    assert cfg.max_tokens == 1234


def test_render_prompt_fills_all_blocks():
    cfg = load_config()
    world_slice = {
        "canon": [
            {"id": 1, "statement": "Lanterns never gutter.", "category": "setting",
             "immutable": True},
            {"id": 2, "statement": "The oak marks the centre.", "category": "geography",
             "immutable": False},
        ],
        "characters": [
            {"id": 5, "name": "Pip", "traits": ["curious", "kind"],
             "relationships": {"hollow": "home"}, "speech_style": "warm",
             "history": ["found the lantern"]},
        ],
        "events": [
            {"id": 9, "order_index": 1, "summary": "Pip lights a lantern.",
             "characters_involved": [5], "world_refs": ["ever-lantern"]},
        ],
    }
    system, user = render_prompt(world_slice, cfg)

    assert system == cfg.system
    assert "[canon:1] (IMMUTABLE) (setting) Lanterns never gutter." in user
    assert "[canon:2] (geography) The oak marks the centre." in user
    assert "(IMMUTABLE)" in user and user.count("(IMMUTABLE)") == 1  # only canon 1
    assert "[character:5] Pip" in user
    assert "speech_style: warm" in user
    assert "[t1] Pip lights a lantern." in user
    # placeholders fully replaced
    assert "{{" not in user


def test_render_prompt_handles_empty_slice():
    cfg = load_config()
    system, user = render_prompt({"canon": [], "characters": [], "events": []}, cfg)
    assert "(none)" in user
    assert "{{" not in user
