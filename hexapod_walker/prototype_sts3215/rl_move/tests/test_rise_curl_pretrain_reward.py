"""Curl-only pretrain reward stage (reward.rise_curl_pretrain,
walkcurr track, 2026-09-13).

Background (`cw-stance50hz-rlonly-risetwophase-s1-canary2m` CANARY
FAIL-MECHANISM): three successive levers on the SAME continuous
height-ramp income (current-headroom-gated `rise_score_prog`,
curl-geometry-gated `rise_score_prog`, and finally a genuine two-phase
freeze-the-ramp-until-curled sub-goal, `goal.rise_curl_gate`) all left
the rise/det flat+bridge failing trajectories within noise of the
ungated parent's own fingerprint. The freeze mechanism demonstrably
FIRES (`env/rise_gate_freeze_ticks` > 0 throughout, unlike the prior
gate whose factor never left 1.0) but a capped freeze inside the full
multi-mode recipe still never gives the policy a strong/isolated
enough reason to discover the coordinated tuck-in motion. Per the
gate's own escalation ("escalate past reward/curriculum shaping
entirely ... or add an explicit curl-only pretraining/BC-free shaping
stage that trains JUST the tuck motion to convergence before ever
wiring in height reward"), this flag turns the per-tick reward for
`is_rise` ticks into JUST the pre-existing curl-progress/curl-milestone
telescoping reward (unchanged formulas, no teacher/anchor/demo signal
anywhere) plus the general actuator/gait safety regularizers that
already apply regardless of mode -- intended as a short warm-start
PRECURSOR stage before resuming the normal full recipe (flag off
again). This is curriculum staging, not another income re-price.

Contract under test:
  - default OFF (`reward.rise_curl_pretrain` unset) is bit-exact: the
    diagnostic key never appears and height/score reward terms fire
    exactly as before.
  - ON: every rise height/score/posture/finish-related reward_* key is
    forced to exactly 0.0 whenever it appears, `reward_curl_progress`
    keeps firing normally, the returned scalar reward equals the sum
    of the surviving (kept) `reward_*` parts, and the diagnostic
    `rise_curl_pretrain_active` flag is exposed for W&B triage.

RESEARCH_RULES "Tests": fast, mechanics only, no rollout ranking, no
artifacts.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.goal_task import SimHexapodGoalEnv

# Height/score/posture/finish terms the pretrain stage must zero.
_DROP_KEYS = (
    "reward_rise_progress", "reward_rise_milestone",
    "reward_rise_score_prog", "reward_rise_score_hold",
    "reward_rise_posture_pen", "reward_rise_finish",
    "reward_rise_footprint_pen", "reward_rise_ref",
    "reward_end_posture",
)
# Terms that must keep firing unchanged (curl signal + general safety).
_KEEP_KEYS = (
    "reward_curl_progress", "reward_curl_milestone",
    "reward_current_hot", "reward_action_rate", "reward_stance",
    "reward_clearance", "reward_flag_leg", "reward_termination",
    "reward_task", "reward_still", "reward_drag_trans",
    "reward_current_income", "reward_support_margin",
    "reward_load_even", "reward_torque_headroom",
)


def _rise_env(seed: int, pretrain: float = 0.0,
              start: str = "flat") -> SimHexapodGoalEnv:
    cfg = load_config()
    cfg.setdefault("actions", {})["max_height_mm"] = 115
    cfg.setdefault("goal", {})["rise_height_mm"] = [90, 90]
    cfg["goal"]["rise_hold_s"] = 0.5
    cfg["goal"]["rise_hold_min_s"] = 0.5
    cfg.setdefault("episode", {})["seconds"] = 8
    cfg.setdefault("reward", {})["rise_score_income"] = 1.0
    if pretrain:
        cfg["reward"]["rise_curl_pretrain"] = pretrain
    env = SimHexapodGoalEnv(cfg=cfg, seed=seed)
    g = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad", "walk"):
        if hasattr(g, f"p_{m}"):
            setattr(g, f"p_{m}", 1.0 if m == "rise" else 0.0)
    g.force_rise_start = start
    return env


def _run(env, n_steps, action):
    env.reset()
    out = []
    for _ in range(n_steps):
        _, r, term, trunc, info = env.step(action)
        out.append((float(r), dict(info)))
        if term or trunc:
            break
    return out


def test_default_off_never_exposes_the_flag_and_height_terms_still_fire():
    infos = [i for _, i in _run(_rise_env(seed=3), 450,
                                 np.full((6,), 0.8, dtype=np.float32))]
    assert not any("rise_curl_pretrain_active" in i for i in infos)
    assert any(i.get("reward_rise_score_prog", 0.0) != 0.0
               for i in infos), \
        "score-income path never fired -- test setup not exercising it"


def test_on_zeros_every_drop_key_every_tick():
    rows = _run(_rise_env(seed=3, pretrain=1.0), 450,
                np.full((6,), 0.8, dtype=np.float32))
    saw_flag = False
    for _, info in rows:
        if info.get("rise_curl_pretrain_active"):
            saw_flag = True
        for k in _DROP_KEYS:
            if k in info:
                assert info[k] == 0.0, f"{k} not zeroed under pretrain"
    assert saw_flag, "pretrain flag never activated on an is_rise tick"


def test_on_keeps_curl_progress_signal_alive():
    rows = _run(_rise_env(seed=3, pretrain=1.0), 450,
                np.full((6,), 0.8, dtype=np.float32))
    curl_vals = [info.get("reward_curl_progress", 0.0) for _, info in rows]
    assert any(v != 0.0 for v in curl_vals), \
        "curl progress reward silenced -- pretrain stage has no signal"


def test_returned_reward_equals_sum_of_surviving_parts():
    rows = _run(_rise_env(seed=3, pretrain=1.0), 450,
                np.full((6,), 0.8, dtype=np.float32))
    for r, info in rows:
        part_sum = sum(v for k, v in info.items()
                        if k.startswith("reward_")
                        and isinstance(v, (int, float)))
        assert r == pytest.approx(part_sum, abs=1e-6), \
            "scalar reward diverges from its own logged reward_* parts"


def test_crouch_start_is_exempt_full_reward_stays_live():
    # Crouch starts have curl_dist ~0 already (nothing to pretrain) --
    # the flag must not touch their reward, so the campaign's
    # already-working rise_crouch_success pathway can't regress just
    # from mixing pretrain-flagged batches into a shared training run.
    on = [i for _, i in _run(_rise_env(seed=3, pretrain=1.0,
                                        start="crouch"), 450,
                             np.full((6,), 0.8, dtype=np.float32))]
    assert not any(i.get("rise_curl_pretrain_active") for i in on), \
        "crouch start was NOT exempted from the pretrain reward gate"
    assert any(i.get("reward_rise_score_prog", 0.0) != 0.0
               for i in on), \
        "crouch start's normal height/score income was suppressed"


def test_on_drops_exactly_the_named_keys_nothing_else_reward_shaped():
    # Same seed/action -> identical physical trajectory in both envs
    # (the flag only changes what's PAID, never the dynamics). Every
    # kept key's per-tick value must be identical on vs off; only the
    # drop-list keys (and the scalar reward, and the new diagnostic
    # flag) may differ.
    off = [i for _, i in _run(_rise_env(seed=3), 450,
                               np.full((6,), 0.8, dtype=np.float32))]
    on = [i for _, i in _run(_rise_env(seed=3, pretrain=1.0), 450,
                             np.full((6,), 0.8, dtype=np.float32))]
    assert len(off) == len(on)
    for a, b in zip(off, on):
        for k in _KEEP_KEYS:
            if k in a or k in b:
                assert a.get(k, 0.0) == pytest.approx(
                    b.get(k, 0.0), abs=1e-9), f"{k} changed under pretrain"
