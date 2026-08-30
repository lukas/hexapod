"""Tests for probe_turn_authority.py (standwalk wave-2 turn-diet gate
instrument, 08-30). Two layers: pure threshold-logic unit tests (no
MuJoCo) and a short env-integration smoke test that pins the tool
against the SCRIPTED reference gait — the sanity control that caught
a real bug (info["walk_wz"] is reward-gated off in this recipe family
and silently reads 0.0 for every policy including the scripted one;
the fix reads env._body_wz() directly, which is unconditional)."""
import numpy as np

from rl_move.sim.probe_turn_authority import summarize, rollout


def _res(wz_cmd, wz_err_med):
    return {"wz_cmd": wz_cmd, "wz_err_med": wz_err_med,
            "frozen_body_wz_err_pred": abs(wz_cmd)}


def test_summarize_flags_frozen_body():
    # achieved error ~= the commanded rate itself -> frozen prediction
    results = [_res(0.25, 0.249), _res(-0.25, 0.248)]
    out = summarize(results)
    assert out["frozen"] is True
    assert "FROZEN-BODY" in out["verdict"]


def test_summarize_passes_real_tracking():
    # achieved error well under half the commanded rate -> tracks
    results = [_res(0.25, 0.03), _res(-0.25, 0.04)]
    out = summarize(results)
    assert out["frozen"] is False
    assert "TRACKS" in out["verdict"]


def test_summarize_margin_is_configurable():
    results = [_res(0.25, 0.15)]  # 0.6x the command
    assert summarize(results, frozen_margin=0.5)["frozen"] is True
    assert summarize(results, frozen_margin=0.7)["frozen"] is False


def test_scripted_gait_env_mechanics_show_real_wz():
    """Env-integration control: a short scripted turn-in-place rollout
    must show wz_med clearly nonzero and well below the frozen-body
    prediction — the exact check that caught the info["walk_wz"] bug
    (that version read 0.0 here too, since it is reward-gated on
    reward.k_walk_yaw > 0, unset by default)."""
    res = rollout(model=None,
                  env_cls_kwargs={"cfg_set": ["goal.walk_yaw_cmd=1"]},
                  wz_cmd=0.25, seed=0, episode_seconds=3.0,
                  policy="scripted")
    assert res["n_walk_ticks"] > 50
    assert res["wz_med"] is not None
    assert abs(res["wz_med"]) > 0.1          # real rotation, not ~0
    assert res["wz_err_med"] < 0.5 * res["frozen_body_wz_err_pred"]
