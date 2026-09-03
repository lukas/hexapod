"""Tests for probe_joint_tracking.py (standwalk item 2 candidate (i)
groundwork, 09-03) -- the live-sim desired-vs-actual joint tracking
instrument. Unit-level ``summarize`` logic plus a short env-
integration smoke test that pins the tool's headline finding: the
scripted teacher's YAW joint saturates the SafetyLayer slew clip on
combined (walk+turn) ticks but NEVER on pure-turn ticks at the same
|wz_cmd| -- the quantified evidence behind the STATUS item-2
candidate (i) hypothesis (SafetyLayer clip differentially removes
rotation on combined ticks)."""
import numpy as np

from rl_move.sim.probe_joint_tracking import rollout, summarize


def _row(vx_cmd, wz_cmd, clip_all=0.0, clip_yaw=0.0,
         sat_all=0.0, sat_yaw=0.0, track_all=0.0, track_yaw=0.0):
    return {
        "vx_cmd": vx_cmd, "wz_cmd": wz_cmd, "n_ticks": 100,
        "clip_gap": {"yaw": {"med_deg": clip_yaw}, "all": {"med_deg": clip_all}},
        "clip_sat_frac": {"yaw": sat_yaw},
        "clip_sat_frac_all": sat_all,
        "track_gap": {"yaw": {"med_deg": track_yaw}, "all": {"med_deg": track_all}},
    }


def test_summarize_splits_pure_turn_vs_combined():
    results = [
        _row(0.0, 0.25, clip_yaw=0.0, sat_yaw=0.0),
        _row(0.0, -0.25, clip_yaw=0.0, sat_yaw=0.0),
        _row(0.08, 0.25, clip_yaw=1.0, sat_yaw=0.48),
        _row(0.08, -0.25, clip_yaw=1.0, sat_yaw=0.48),
    ]
    out = summarize(results)
    assert out["pure_turn"]["n_cells"] == 2
    assert out["combined"]["n_cells"] == 2
    assert out["pure_turn"]["clip_sat_frac_yaw"] == 0.0
    assert out["combined"]["clip_sat_frac_yaw"] == 0.48


def test_summarize_ignores_zero_command_rows():
    # a hold/idle row (vx=wz=0) matches neither bucket
    results = [_row(0.0, 0.0)]
    out = summarize(results)
    assert out["pure_turn"] is None
    assert out["combined"] is None


def test_scripted_env_shows_yaw_clip_asymmetry():
    """Env-integration control (short episode): at the SAME |wz_cmd|,
    the scripted teacher's yaw joint must show materially MORE
    SafetyLayer clip saturation on a combined (vx!=0) tick than on a
    pure-turn (vx==0) tick -- this is the finding a future
    tripod_gait.py geometry fix must falsify against."""
    cfg = ["env.model_source=mesh", "control.hz=100",
           "goal.walk_yaw_cmd=1", "goal.walk_phase_run_on_yaw=1"]
    pure = rollout(cfg_set=cfg, wz_cmd=0.25, vx_cmd=0.0, seed=0,
                   episode_seconds=5.0)
    combined = rollout(cfg_set=cfg, wz_cmd=0.25, vx_cmd=0.08, seed=0,
                        episode_seconds=5.0)
    assert pure["n_ticks"] > 50
    assert combined["n_ticks"] > 50
    assert pure["clip_sat_frac"]["yaw"] < 0.05
    assert combined["clip_sat_frac"]["yaw"] > 0.30
    assert (combined["clip_sat_frac"]["yaw"]
            > pure["clip_sat_frac"]["yaw"] + 0.2)
