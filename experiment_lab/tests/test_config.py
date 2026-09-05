from hexapod_lab.config import Settings


def test_codex_reasoning_effort_defaults_to_medium(monkeypatch):
    monkeypatch.delenv("HEXAPOD_CODEX_REASONING_EFFORT", raising=False)

    assert Settings.__dataclass_fields__["codex_reasoning_effort"].default == "medium"
    assert Settings.from_env().codex_reasoning_effort == "medium"
