import json
import types

import pytest

from worldstate import SqliteWorldStore
from generation import GenerationError, generate_story, load_config, render_prompt


# --- a fake Anthropic client (no SDK, no network, no key) ------------------

class FakeUsage:
    def __init__(self, i, o):
        self.input_tokens = i
        self.output_tokens = o


class FakeResponse:
    def __init__(self, payload, model, stop_reason="end_turn"):
        self.content = [types.SimpleNamespace(type="text", text=json.dumps(payload))]
        self.model = model
        self.stop_reason = stop_reason
        self.usage = FakeUsage(100, 200)


class FakeMessages:
    def __init__(self, payload, model="claude-opus-4-8", stop_reason="end_turn"):
        self.payload = payload
        self.model = model
        self.stop_reason = stop_reason
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return FakeResponse(self.payload, self.model, self.stop_reason)


class FakeClient:
    def __init__(self, payload, **kw):
        self.messages = FakeMessages(payload, **kw)


@pytest.fixture()
def seeded_store():
    s = SqliteWorldStore.open(":memory:")
    c1 = s.add_canon("Lanterns never gutter.", "setting", immutable=True)
    c2 = s.add_canon("Nothing frightening happens.", "tone", immutable=True)
    pip = s.add_character("Pip", traits=["curious"], speech_style="warm")
    bramble = s.add_character("Bramble", traits=["cautious"])
    s.write_events([
        {"order_index": 1, "summary": "Pip lights a lantern.",
         "characters_involved": [pip.id]},
    ])
    try:
        yield s, {"c1": c1.id, "c2": c2.id, "pip": pip.id, "bramble": bramble.id}
    finally:
        s.close()


def test_generate_returns_story_and_used_ids(seeded_store):
    store, ids = seeded_store
    payload = {
        "story": "Pip lit the lantern and the Hollow glowed softly. The end.",
        "canon_used": [ids["c1"], ids["c2"]],
        "characters_used": [ids["pip"]],
    }
    client = FakeClient(payload)

    result = generate_story(store, character_ids=[ids["pip"], ids["bramble"]],
                            recent_events=5, client=client)

    assert "Pip" in result.story
    assert result.canon_used == [ids["c1"], ids["c2"]]
    assert result.characters_used == [ids["pip"]]
    assert result.model == "claude-opus-4-8"
    assert result.usage == {"input_tokens": 100, "output_tokens": 200}


def test_records_both_used_subset_and_full_provided_slice(seeded_store):
    store, ids = seeded_store
    payload = {"story": "A gentle tale.", "canon_used": [ids["c1"]],
               "characters_used": [ids["pip"]]}
    client = FakeClient(payload)

    result = generate_story(store, character_ids=[ids["pip"], ids["bramble"]],
                            client=client)

    # self-reported subset
    assert result.canon_used == [ids["c1"]]
    assert result.used_canon_statements() == ["Lanterns never gutter."]
    assert result.used_character_names() == ["Pip"]
    # full provided slice retained
    assert set(result.provided_canon_ids()) == {ids["c1"], ids["c2"]}
    assert set(result.provided_character_ids()) == {ids["pip"], ids["bramble"]}


def test_reads_from_backbone_and_passes_canon_into_prompt(seeded_store):
    store, ids = seeded_store
    client = FakeClient({"story": "x", "canon_used": [], "characters_used": []})

    generate_story(store, character_ids=[ids["pip"]], client=client)

    kwargs = client.messages.last_kwargs
    assert kwargs["model"] == "claude-opus-4-8"
    # the retrieved canon was rendered into the user prompt, with immutability flags
    user = kwargs["messages"][0]["content"]
    assert f"[canon:{ids['c1']}]" in user
    assert "(IMMUTABLE)" in user
    assert "[character:" in user
    # structured output + adaptive thinking are requested
    assert kwargs["output_config"]["format"]["type"] == "json_schema"
    assert kwargs["thinking"] == {"type": "adaptive"}


def test_generation_is_read_only(seeded_store):
    store, ids = seeded_store
    before = store.get_world_slice()
    client = FakeClient({"story": "x", "canon_used": [], "characters_used": []})

    generate_story(store, character_ids=[ids["pip"]], client=client)

    after = store.get_world_slice()
    assert len(after["canon"]) == len(before["canon"])
    assert len(after["characters"]) == len(before["characters"])
    assert len(after["events"]) == len(before["events"])


def test_refusal_raises(seeded_store):
    store, ids = seeded_store
    client = FakeClient({"story": "", "canon_used": [], "characters_used": []},
                        stop_reason="refusal")
    with pytest.raises(GenerationError):
        generate_story(store, character_ids=[ids["pip"]], client=client)


def test_character_filter_scopes_slice(seeded_store):
    store, ids = seeded_store
    client = FakeClient({"story": "x", "canon_used": [], "characters_used": []})

    result = generate_story(store, character_ids=[ids["pip"]], client=client)
    # only Pip was retrieved and provided
    assert result.provided_character_ids() == [ids["pip"]]
