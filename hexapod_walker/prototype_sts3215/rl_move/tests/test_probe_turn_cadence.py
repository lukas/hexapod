"""Cadence probe: guard generalization stays bit-exact at period_scale=1,
rejects the raw-IK-None fallback at any dosed period_scale too, and the
CLI enforces the SCALE_PERIOD bounds instead of silently clamping."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from rl_move.sim import probe_turn_cadence as cadence  # noqa: E402
from rl_move.sim import probe_turn_stancearm as probe  # noqa: E402
from hexapod_core.tripod_gait import TripodGait  # noqa: E402


CELLS = [(0.08, 0.15), (0.08, -0.15), (0.08, 0.0)]


def test_period_scale_default_is_bit_exact_with_stance_baseline():
    """period_scale=1.0 must reproduce the original stance-arm guard's
    own pinned margins/tick-count exactly -- the generalization must not
    change baseline behavior."""
    result = probe.feasibility_guard(20.0, 100.0, CELLS)
    assert result["raw_ik_calls"] == 7200
    assert result["raw_ik_failures"] == 0
    assert result["period_scale"] == 1.0
    assert result["n_ticks_per_cell"] == 400
    assert [result["joint_margins"][axis]["margin_deg"]
            for axis in ("yaw", "hip", "knee")] == pytest.approx(
                [19.613218251838322, 18.24994375209038, 45.268249966008966],
                rel=0, abs=1e-12)


@pytest.mark.parametrize("period_scale", [0.75, 1.5, 2.0])
def test_dosed_period_scale_still_covers_full_cycles_with_zero_ik_failures(
        period_scale):
    result = probe.feasibility_guard(20.0, 100.0, CELLS,
                                     period_scale=period_scale)
    assert result["raw_ik_failures"] == 0
    assert result["period_scale"] == period_scale
    # >=3 full effective periods per cell, never fewer ticks than the
    # original 400-tick (4s) baseline sweep.
    period_eff = TripodGait().period * period_scale
    assert result["n_ticks_per_cell"] >= max(400, int(3 * period_eff / 0.01))
    for axis in ("yaw", "hip", "knee"):
        assert result["joint_margins"][axis]["margin_deg"] >= 2.0


@pytest.mark.parametrize("fail_at", [1, 17])
def test_raw_ik_failure_cannot_pass_at_a_dosed_cadence_either(
        monkeypatch, fail_at):
    module = sys.modules[probe.TripodGait.__module__]
    original = module._leg_ik
    calls = 0

    def fail_once(target):
        nonlocal calls
        calls += 1
        return None if calls == fail_at else original(target)

    monkeypatch.setattr(module, "_leg_ik", fail_once)
    with pytest.raises(SystemExit, match="raw IK failed"):
        probe.feasibility_guard(20.0, 100.0, CELLS, period_scale=1.5)
    assert module._leg_ik is fail_once


def test_cli_rejects_period_scale_outside_gait_bounds(tmp_path, capsys):
    cfg_json = tmp_path / "cfg.json"
    cfg_json.write_text("[]")
    out = tmp_path / "out.json"
    argv = ["prog", "--cfg-json", str(cfg_json), "--cells", "0.08:0.15",
            "--period-scale", "3.0", "--out", str(out)]
    monkeypatch_argv = sys.argv
    sys.argv = argv
    try:
        with pytest.raises(SystemExit, match="outside"):
            cadence.main()
    finally:
        sys.argv = monkeypatch_argv
    assert not out.exists()
