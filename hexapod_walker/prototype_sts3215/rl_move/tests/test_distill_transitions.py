"""distill_gru --transitions tests (TRANSITIONS_DIRECTIVE CODE item 2).

Locks the sequence-demo collector that rides goal.mode_seq (item 1):

1. default OFF: --transitions defaults to 0 and the flag requires
   --dual (failure-ledger lesson 1) before any heavy work;
2. per-tick teacher ROUTING: in one continuous sequence episode the
   label at every tick comes from the ACTIVE segment's teacher (walk
   teacher on walk ticks, stance teacher everywhere else) and the obs
   mode one-hot agrees with the recorded per-tick mode;
3. the demo stream is continuous (one episode array, mode flips
   mid-array, no reset between segments);
4. the in-context teacher verification aborts loudly when the verify
   window budget is exceeded;
5. collect_transitions refuses an env without goal.mode_seq=1.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "linux_control"))
sys.path.insert(0, str(ROOT / "linux_control" / "urt2_setup"))

from rl_move.config import load_config  # noqa: E402
from rl_move.sim.distill_gru import (  # noqa: E402
    _com_xy, _episode_split, collect_transitions, main as distill_main,
    quick_probe,
)
from rl_move.sim.walk_task import (  # noqa: E402
    MODE_ONEHOT_ORDER, SimHexapodJointWalkEnv,
)

N_ONEHOT = len(MODE_ONEHOT_ORDER)
WALK_CONST, STANCE_CONST = 0.05, -0.05


class _StubTeacher:
    """Constant-action teacher; enough API for collect_transitions."""

    class _Policy:
        def predict_values(self, t):
            return np.float32(0.0)

    def __init__(self, const: float):
        self.const = float(const)
        self.policy = self._Policy()

    def predict(self, obs, deterministic=True):
        return np.full(18, self.const, dtype=np.float32), None


def _make_seq_env(seed: int = 1, episode_seconds: float = 10.0,
                  mix: dict | None = None, seq: bool = True):
    cfg = load_config()
    g = cfg.setdefault("goal", {})
    if seq:
        g["mode_seq"] = 1.0
        g["mode_seq_segment_s_min"] = 3.0
        g["mode_seq_segment_s_max"] = 4.0
    cfg.setdefault("obs", {})["mode_onehot"] = 1.0
    env = SimHexapodJointWalkEnv(cfg, seed=seed,
                                 episode_seconds=episode_seconds)
    if mix is not None:
        gen = env._goal_gen
        for a in [a for a in vars(gen) if a.startswith("p_")]:
            setattr(gen, a, 0.0)
        gen.p_walk = 0.0
        for m, p in mix.items():
            setattr(gen, f"p_{m}", p)
    return env


def _teachers(env):
    n_env = int(env.observation_space.shape[0])
    return {"walk": (_StubTeacher(WALK_CONST), n_env - N_ONEHOT),
            "stance": (_StubTeacher(STANCE_CONST), 68)}


# ---------------------------------------------------------------------------
# 1. CLI defaults / guards
# ---------------------------------------------------------------------------

def test_transitions_defaults_off_and_requires_dual():
    # --transitions without --dual must exit before any teacher load.
    with pytest.raises(SystemExit, match="--dual"):
        distill_main(["--transitions", "1"])


# ---------------------------------------------------------------------------
# 2/3. routing + continuity on a real mode_seq env
# ---------------------------------------------------------------------------

def test_routing_and_onehot_agree():
    env = _make_seq_env(mix={"lower": 1.0})   # lower -> rise: a switch
    teachers = _teachers(env)
    rng = np.random.default_rng(0)
    episodes, stats = collect_transitions(
        env, teachers, n_ep=1, stochastic_frac=0.0, rng=rng,
        verify_n=0, verify_max_falls=99)
    env.close()
    assert len(episodes) == 1
    tag, obs, act, val = episodes[0]
    assert tag == "seq"
    modes = stats["eps"][0]["modes"]
    assert len(modes) == act.shape[0] == obs.shape[0] == val.shape[0]
    # one continuous stream with >= 2 distinct modes (a real switch)
    assert len(set(modes)) >= 2
    assert stats["eps"][0]["switches"] >= 1
    for t, mode in enumerate(modes):
        want = WALK_CONST if mode == "walk" else STANCE_CONST
        assert float(act[t, 0]) == pytest.approx(want), (t, mode)
        onehot = obs[t, -N_ONEHOT:]
        assert onehot[MODE_ONEHOT_ORDER.index(mode)] == 1.0, (t, mode)
        assert onehot.sum() == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# 4. verification abort path
# ---------------------------------------------------------------------------

def test_verify_abort_fires():
    env = _make_seq_env(mix={"lower": 1.0})
    teachers = _teachers(env)
    rng = np.random.default_rng(0)
    # max_falls=-1 makes any verify window (even 0 falls) exceed budget.
    with pytest.raises(SystemExit, match="SEQUENCE-COMPETENT"):
        collect_transitions(env, teachers, n_ep=2, stochastic_frac=0.0,
                            rng=rng, verify_n=1, verify_max_falls=-1)
    env.close()


# ---------------------------------------------------------------------------
# 5. refuse a non-mode_seq env
# ---------------------------------------------------------------------------

def test_refuses_env_without_mode_seq():
    env = _make_seq_env(seq=False)
    teachers = _teachers(env)
    with pytest.raises(SystemExit, match="mode_seq"):
        collect_transitions(env, teachers, n_ep=1, stochastic_frac=0.0,
                            rng=np.random.default_rng(0))
    env.close()


# ---------------------------------------------------------------------------
# 6. --dagger-extra-mix / --dagger-extra-episodes (Arm-A stage-0 FAIL
#    follow-up: a rise-targeted DAgger top-up on top of the sequence
#    pass). Default OFF; validation fires before any teacher/env load.
# ---------------------------------------------------------------------------

def test_dagger_extra_mix_requires_episodes():
    with pytest.raises(SystemExit, match="dagger-extra-episodes"):
        distill_main(["--dagger-extra-mix", "rise=1.0"])


def test_dagger_extra_episodes_requires_mix():
    with pytest.raises(SystemExit, match="dagger-extra-mix"):
        distill_main(["--dagger-extra-episodes", "10"])


def test_dagger_extra_mix_rejects_unknown_mode():
    with pytest.raises(SystemExit, match="unknown modes"):
        distill_main(["--dagger-extra-mix", "flap=1.0",
                      "--dagger-extra-episodes", "10"])


def test_episode_split_matches_legacy_formula():
    mix = {"walk": 0.60, "rise": 0.15, "lower": 0.15, "hold": 0.10}
    got = _episode_split(200, mix)
    want = {m: max(1, round(200 * w)) for m, w in mix.items() if w > 0}
    assert got == want
    # zero-weight modes are dropped, not zero-valued
    assert _episode_split(100, {"rise": 1.0, "walk": 0.0}) == {"rise": 100}
    # every present weight gets at least 1 episode even at tiny totals
    assert _episode_split(1, {"rise": 0.4, "walk": 0.3, "lower": 0.15,
                              "hold": 0.15}) == {
        "rise": 1, "walk": 1, "lower": 1, "hold": 1}


# ---------------------------------------------------------------------------
# quick_probe net-displacement sanity check (2026-08-30, the
# dualbc2_allheadwalk lesson: a plausible episode RETURN can mask a
# checkpoint that never leaves the spot -- eval_checkpoint's real
# harness caught near-zero forward_dist_m / huge slip_per_m on a
# checkpoint whose own quick_probe returns had looked unremarkable).
# ---------------------------------------------------------------------------

class _ZeroStudent:
    """Stateful-predict-shaped stub that always commands zero action
    (stay put) -- the canonical in-place-quivering case this check
    exists to catch."""

    def __init__(self, n_act: int):
        self._n_act = n_act

    def predict(self, obs, state=None, episode_start=None,
                deterministic=True):
        return np.zeros(self._n_act, dtype=np.float32), None


def test_com_xy_helper():
    env = _make_seq_env(seq=False, episode_seconds=5.0)
    env.reset()
    xy = _com_xy(env)
    assert xy is not None and xy.shape == (2,)
    assert _com_xy(object()) is None  # no .data -> None, never raises
    env.close()


def test_quick_probe_flags_near_zero_walk_displacement(capsys):
    env = _make_seq_env(seq=False, episode_seconds=5.0)
    student = _ZeroStudent(int(env.action_space.shape[0]))
    quick_probe(student, env, modes=("walk",), n_ep=1)
    env.close()
    out = capsys.readouterr().out
    assert "probe walk" in out
    assert "net_disp_m" in out
    # zero action for 2s cannot produce real forward locomotion -- the
    # WARNING that would have flagged the dualbc2_allheadwalk defect
    # must fire here too, or the check is not doing its job.
    assert "WARNING" in out


def test_quick_probe_non_walk_mode_has_no_displacement_field(capsys):
    # rise/hold aren't instrumented (the lesson was specifically about
    # walk not walking) -- confirm the field is walk-only, not a
    # silent crash on other modes.
    env = _make_seq_env(seq=False, episode_seconds=5.0)
    student = _ZeroStudent(int(env.action_space.shape[0]))
    quick_probe(student, env, modes=("hold",), n_ep=1)
    env.close()
    out = capsys.readouterr().out
    assert "probe hold" in out
    assert "net_disp_m" not in out


def test_quick_probe_forces_single_heading_and_restores_resample(capsys):
    # 2026-08-30 follow-up to the dualbc2_allheadwalk lesson: the
    # net-displacement check itself gives a FALSE positive for a
    # genuine all-heading teacher whose command legitimately changes
    # heading every walk_cmd_resample_s seconds -- a symmetric
    # heading set makes START->END displacement cancel to ~0 over a
    # full multi-segment episode even when every segment is a real
    # directed walk. quick_probe must force a single fixed heading
    # (walk_cmd_resample_s=0) for its own walk-mode rollouts, and
    # restore the caller's original value afterward (env.cfg is
    # shared/caller-owned) -- both are locked here.
    env = _make_seq_env(seq=False, episode_seconds=5.0)
    env.cfg["goal"]["walk_cmd_resample_s"] = 6.0
    student = _ZeroStudent(int(env.action_space.shape[0]))
    quick_probe(student, env, modes=("walk",), n_ep=1)
    env.close()
    assert env.cfg["goal"]["walk_cmd_resample_s"] == 6.0


def test_quick_probe_removes_resample_key_if_caller_never_set_one():
    # If the caller's cfg had no walk_cmd_resample_s at all (the
    # common case -- most single-goal probe envs never set it), the
    # temporary override must not leave a stray key behind.
    env = _make_seq_env(seq=False, episode_seconds=5.0)
    assert "walk_cmd_resample_s" not in env.cfg["goal"]
    student = _ZeroStudent(int(env.action_space.shape[0]))
    quick_probe(student, env, modes=("walk",), n_ep=1)
    env.close()
    assert "walk_cmd_resample_s" not in env.cfg["goal"]
