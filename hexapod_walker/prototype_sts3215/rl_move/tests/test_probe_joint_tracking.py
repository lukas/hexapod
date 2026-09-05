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


def test_rollout_swing_stance_split_present_and_partitions_all_ticks():
    """standwalk Next item 2(i) follow-up (09-05): every recorded tick
    must be attributed to swing OR stance (never both, never neither)
    for the leg-major axis columns, and the split keys must exist on
    the returned dict (used by ``summarize``'s swing/stance
    comparison)."""
    cfg = ["env.model_source=mesh", "control.hz=100",
           "goal.walk_yaw_cmd=1", "goal.walk_phase_run_on_yaw=1"]
    res = rollout(cfg_set=cfg, wz_cmd=0.25, vx_cmd=0.08, seed=0,
                  episode_seconds=5.0)
    assert res["n_ticks"] > 50
    split = res["clip_sat_frac_swing_stance"]["all"]
    assert split["swing"] is not None and split["stance"] is not None
    # swing_tick_frac_all is the fraction of (tick, leg) cells
    # currently swinging -- must be strictly between 0 and 1 (3 of 6
    # legs swing at any instant, so ~0.5, not exactly since ramp-up
    # ticks are excluded from the recorded window but boundary ticks
    # can skew it slightly).
    assert 0.2 < res["swing_tick_frac_all"] < 0.8
    assert "swing_all_med_deg" in res["clip_gap"]
    assert "stance_all_med_deg" in res["clip_gap"]


def test_rollout_group_duty_skew_is_forwarded_and_bit_exact_at_zero():
    """``group_duty_skew=0.0`` (default) must reproduce the pre-09-05
    numbers exactly (bit-exact-off contract shared by every other dose
    knob in this codebase); a nonzero skew must actually change the
    swing/stance tick-count split (since it re-times which legs get
    more swing time)."""
    cfg = ["env.model_source=mesh", "control.hz=100",
           "goal.walk_yaw_cmd=1", "goal.walk_phase_run_on_yaw=1"]
    base = rollout(cfg_set=cfg, wz_cmd=0.25, vx_cmd=0.08, seed=0,
                   episode_seconds=5.0, group_duty_skew=0.0)
    zero_explicit = rollout(cfg_set=cfg, wz_cmd=0.25, vx_cmd=0.08, seed=0,
                            episode_seconds=5.0)
    assert base["clip_gap"]["all"]["med_deg"] == (
        zero_explicit["clip_gap"]["all"]["med_deg"])
    assert base["swing_tick_frac_all"] == zero_explicit["swing_tick_frac_all"]
    # invariant (exactly 3/6 legs swing at any instant, any skew --
    # see test_tripod_gait_group_duty_skew.py) means the (tick, leg)
    # swing FRACTION never moves; the swing/stance SATURATION split
    # (what a duty-skew dose is actually meant to change) must.
    assert base["swing_tick_frac_all"] == 0.5

    dosed = rollout(cfg_set=cfg, wz_cmd=0.25, vx_cmd=0.08, seed=0,
                    episode_seconds=5.0, group_duty_skew=0.3)
    assert dosed["swing_tick_frac_all"] == 0.5  # invariant holds at dose too
    # yaw clip_gap (the axis this candidate targets) must actually
    # move at a nonzero dose -- both the swing and stance buckets.
    assert (dosed["clip_gap"]["yaw"]["swing_med_deg"]
            != base["clip_gap"]["yaw"]["swing_med_deg"])
    assert (dosed["clip_sat_frac_swing_stance"]["all"]["swing"]
            != base["clip_sat_frac_swing_stance"]["all"]["swing"])


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
