"""HEXAPOD_SAFETY_MAX_DELTA_Q_DEG override for
`rl_move.config.load_config` (2026-09-30, primitive-family calibrated-
suite regression DIG-IN).

Mirrors `test_config_control_hz_override.py`'s pattern exactly. Unlike
that 08-25 case (investigated, found only a partial explanation, and
deliberately left unwired), THIS override is wired into
`tests/conftest.py`'s defaults: `git bisect` + cross-model-family replay
found a complete, mechanistic root cause for the 28-test regression that
followed config.yaml's `safety.max_delta_q_deg` default flip 0.375 ->
1.76 on 2026-09-27 (commit 867835836) -- see that file's own docstring
for the full mechanism and reproduction.
"""
from __future__ import annotations


from rl_move.config import load_config


def test_unset_env_var_is_bit_exact(monkeypatch):
    monkeypatch.delenv("HEXAPOD_SAFETY_MAX_DELTA_Q_DEG", raising=False)
    a = load_config()
    b = load_config()
    assert a == b
    import yaml
    from rl_move.config import DEFAULT_CONFIG
    raw = yaml.safe_load(DEFAULT_CONFIG.read_text())
    assert a["safety"]["max_delta_q_deg"] == raw["safety"]["max_delta_q_deg"]


def test_set_env_var_overrides_only_max_delta_q_deg(monkeypatch):
    monkeypatch.delenv("HEXAPOD_SAFETY_MAX_DELTA_Q_DEG", raising=False)
    baseline = load_config()
    monkeypatch.setenv("HEXAPOD_SAFETY_MAX_DELTA_Q_DEG", "0.375")
    overridden = load_config()
    assert overridden["safety"]["max_delta_q_deg"] == 0.375
    baseline_no_dq = dict(baseline["safety"])
    overridden_no_dq = dict(overridden["safety"])
    baseline_no_dq.pop("max_delta_q_deg")
    overridden_no_dq.pop("max_delta_q_deg")
    assert baseline_no_dq == overridden_no_dq
    assert {k: v for k, v in baseline.items() if k != "safety"} == \
        {k: v for k, v in overridden.items() if k != "safety"}


def test_value_always_parses_as_float(monkeypatch):
    monkeypatch.setenv("HEXAPOD_SAFETY_MAX_DELTA_Q_DEG", "2")
    val = load_config()["safety"]["max_delta_q_deg"]
    assert val == 2.0
    assert isinstance(val, float)


def test_conftest_pins_legacy_value_for_primitive_suite():
    """The suite-wide conftest default this cycle wired in -- confirms
    the pin is actually active for every test in this directory (not
    just directly testing the override mechanism above)."""
    import os
    assert os.environ.get("HEXAPOD_SAFETY_MAX_DELTA_Q_DEG") == "0.375"
    assert load_config()["safety"]["max_delta_q_deg"] == 0.375
