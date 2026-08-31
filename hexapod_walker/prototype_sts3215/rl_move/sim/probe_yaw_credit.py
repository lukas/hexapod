"""probe_yaw_credit.py — per-tick reward-vs-value (TD-residual) trace
for the standwalk turn-authority credit-assignment dig-in (08-31).

WHY: seven independent turn-authority mechanism-class canaries on the
``dualbc5_turncap`` lineage (BC-anchor dose 3.0/1.0/0.3, anchor
turn-tick-targeted skip, BC-anchor isolate-update, PPO ent-coef 4x,
walk-core ``log_std`` raise to std 0.45 AND 0.82) all FAILED
identically: ``probe_turn_authority`` reads a frozen body (wz_med ~0
both signs) despite ``env/reward_walk_yaw`` firing a real, sizeable
per-tick signal early in training (~1.0 decaying to ~0.12, per
standwalk STATUS 08-31 ~07:0x). Every FAIL's own gate text named the
same next step: "the raw per-tick reward-vs-value/credit-assignment
trace" — this module IS that tool. It did not exist before this.

WHAT IT DOES: holds a fixed body-frame ``wz`` command (pure
turn-in-place, same convention as ``probe_turn_authority``) and steps
a DUAL-CORE GRU checkpoint (``DualGruActorCriticPolicy`` — this is
the ONLY policy family that applies; a plain MLP/single-GRU checkpoint
should call ``policy.predict_values()`` directly instead) through its
OWN ``forward()`` path, threading BOTH the actor's and the critic's
recurrent state as an ``RNNStates(pi, vf)`` pair exactly the way
``RecurrentPPO.collect_rollouts`` does during training.  This is
deliberately NOT ``model.predict()`` — that SB3 convenience method
(used by every other eval/probe tool here) only threads the ACTOR's
hidden state; the critic's own recurrent state silently resets to
zero on every call, so any naive "call predict_values() after
predict()" trace would score a critic that never actually saw the
episode. Getting this right is the whole point of the tool.

At every tick after the wz ramp, in ANY goal_mode (not filtered — the
TD chain must stay whole across mode transitions for the bootstrap to
be meaningful), it records: the achieved body ``wz``
(``env._body_wz()``), the total step reward, the ``reward_walk_yaw``
income (``info["reward_walk_yaw"]``, 0.0 when absent/off), and the
critic's value estimate V(s) BEFORE the action (the state carried
INTO that tick). After the rollout it computes the one-step TD
residual ``delta_t = r_t + gamma * V(s_{t+1}) - V(s_t)`` over the
WHOLE episode (terminal bootstrap V=0), then restricts to the
wz-probe's own scored window (walk-mode, post-ramp — the exact window
``probe_turn_authority`` scores) for the credit-assignment read:

  - Pearson corr(reward_walk_yaw, delta_t) — does the critic notice
    a real, firing reward-yaw income at all?
  - Pearson corr(wz * sign(wz_cmd), delta_t) — does moving TOWARD the
    command (even by policy-noise chance, since the policy itself
    achieves ~0 net wz) earn a better-than-expected outcome, or does
    the critic not distinguish "toward" from "away" ticks?
  - top-quartile vs bottom-quartile mean delta_t by
    ``wz * sign(wz_cmd)`` — a more robust (non-Pearson) version of the
    same question: are the FEW noise-ticks that happen to nudge the
    body toward the command reinforced (top mean > bottom mean),
    ignored (indistinguishable), or actively punished (top < bottom)?

The straight ``delta_t`` reads above are trivially biased toward
"CREDIT-REWARDS": ``r_t`` (which includes ``reward_walk_yaw`` itself)
is a literal ADDEND of ``delta_t``, so a live reward channel alone
guarantees a strong same-tick correlation with no forward-looking
information at all. The decisive, non-tautological question is
whether the CRITIC anticipates any of this — does its OWN belief
about the future change when the body happens to nudge toward the
command, i.e. ``value_delta_t = gamma*V(s_{t+1}) - V(s_t)`` ALONE
(``= delta_t - r_t``, reward excluded)? The same three statistics are
reported again on ``value_delta`` (``corr_*_vs_value_delta``,
``value_delta_mean_{top,bottom}_quartile_toward``,
``forward_verdict``) — THIS is the real credit-assignment read; the
plain ``delta_t``/``verdict`` fields are reported for completeness
(and to catch a dead-reward-channel confound) but should not be read
as evidence of forward credit by themselves.

A CREDIT-BLIND or CREDIT-PUNISHES ``forward_verdict`` on a checkpoint
whose reward
channel is independently confirmed live (structural audit, standwalk
STATUS 08-31: no anchor/loadslip-gate confound on pure-turn ticks, no
generic angular-velocity penalty exists) is direct evidence for the
architecture/value-credit-assignment hypothesis the seven exploration/
salience canaries left as the only remaining suspect — not a "reward
is dead" finding (already ruled out) and not something another
reward-weight dose can fix.

Usage:
  uv run python -m rl_move.sim.probe_yaw_credit CKPT.zip \
      --cfg-set goal.walk_yaw_cmd=1 --cfg-set goal.walk_phase_run_on_yaw=1 \
      --cfg-set env.model_source=mesh --cfg-set control.hz=100 \
      --wz-cmds 0.25,-0.25 --seeds 0,1 --out logs/ckpt_eval/yaw_credit.json
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "2")

import argparse
import json
import sys
from pathlib import Path

import numpy as np

_RL = Path(__file__).resolve().parents[1]
_PROTO = _RL.parent
for _p in (_PROTO, _PROTO / "linux_control"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from .probe_turn_authority import make_env  # noqa: E402


# ---------------------------------------------------------------------
# Pure math — unit-testable without torch/MuJoCo.
# ---------------------------------------------------------------------

def td_residuals(rewards, values, gamma: float) -> np.ndarray:
    """One-step TD residual delta_t = r_t + gamma*V(s_{t+1}) - V(s_t).

    ``rewards`` has length N; ``values`` has length N+1 (values[i] is
    V(s_i) BEFORE action i, values[N] is the bootstrap value of the
    tick after the last recorded reward — pass 0.0 there for a
    terminal episode). Returns an array of length N.
    """
    r = np.asarray(rewards, dtype=np.float64)
    v = np.asarray(values, dtype=np.float64)
    if len(v) != len(r) + 1:
        raise ValueError(
            f"values must be len(rewards)+1 (got {len(v)} vs "
            f"{len(r)}+1)")
    return r + gamma * v[1:] - v[:-1]


def _safe_pearson(a, b) -> float | None:
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    if len(a) < 2 or np.std(a) < 1e-12 or np.std(b) < 1e-12:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def _quartile_split(score: np.ndarray, value: np.ndarray,
                     frac: float = 0.25) -> tuple[float | None, float | None]:
    """Mean ``value`` among the top/bottom ``frac`` of ticks by
    ``score``. None if too few ticks to form a nonempty quartile."""
    n = len(score)
    k = max(1, int(round(n * frac)))
    if n < 4:
        return None, None
    order = np.argsort(score)
    bottom = value[order[:k]]
    top = value[order[-k:]]
    return float(np.mean(top)), float(np.mean(bottom))


def _credit_verdict(toward: np.ndarray, score: np.ndarray,
                     label: str) -> tuple[str, dict]:
    """Shared top/bottom-quartile-by-``toward`` verdict logic, applied
    to either the full TD residual or the reward-EXCLUDED value delta
    (``score``). Returns (verdict_string, {top,bottom,std} fields)."""
    n = len(score)
    top_mean, bot_mean = (_quartile_split(toward, score) if n else
                          (None, None))
    if top_mean is None or bot_mean is None:
        verdict = "INSUFFICIENT-TICKS"
    else:
        spread = float(np.std(score)) if n else 0.0
        gap = top_mean - bot_mean
        if spread < 1e-9:
            verdict = f"CREDIT-BLIND ({label} never moves)"
        elif gap > 0.25 * spread:
            verdict = f"CREDIT-REWARDS ({label}: toward-command ticks score higher)"
        elif gap < -0.25 * spread:
            verdict = f"CREDIT-PUNISHES ({label}: toward-command ticks score lower)"
        else:
            verdict = f"CREDIT-BLIND ({label}: toward vs away indistinguishable)"
    return verdict, {
        f"{label}_mean_top_quartile_toward": top_mean,
        f"{label}_mean_bottom_quartile_toward": bot_mean,
        f"{label}_std": float(np.std(score)) if n else None,
    }


def summarize(masked: dict) -> dict:
    """Aggregate the scored-window arrays into the credit-assignment
    read. ``masked`` holds equal-length numpy arrays: ``wz``,
    ``wz_cmd`` (scalar), ``reward_walk_yaw``, ``td_residual``, and
    optionally ``value_delta`` (``gamma*V(s')-V(s)`` ALONE, reward
    excluded — see module docstring: ``td_residual`` trivially
    correlates with ``reward_walk_yaw`` because the reward IS a term
    in it; ``value_delta`` isolates whether the CRITIC's own belief
    about the future changes when the body happens to nudge toward
    the command, the genuine forward-looking credit-assignment
    question. Missing/all-None ``value_delta`` degrades gracefully
    (its fields come back None) for callers that only have the raw
    per-tick reward/value pair, not a value_delta array."""
    wz = np.asarray(masked["wz"], dtype=np.float64)
    wz_cmd = float(masked["wz_cmd"])
    ryaw = np.asarray(masked["reward_walk_yaw"], dtype=np.float64)
    td = np.asarray(masked["td_residual"], dtype=np.float64)
    n = len(td)
    sign = 1.0 if wz_cmd >= 0 else -1.0
    toward = wz * sign
    corr_yaw_td = _safe_pearson(ryaw, td) if n else None
    corr_toward_td = _safe_pearson(toward, td) if n else None
    verdict, td_fields = _credit_verdict(toward, td, "td")

    out = {
        "n_ticks": n,
        "corr_reward_walk_yaw_vs_td": corr_yaw_td,
        "corr_wz_toward_cmd_vs_td": corr_toward_td,
        "td_mean_top_quartile_toward": td_fields["td_mean_top_quartile_toward"],
        "td_mean_bottom_quartile_toward": td_fields["td_mean_bottom_quartile_toward"],
        "td_std": td_fields["td_std"],
        "verdict": verdict,
    }

    vdelta = masked.get("value_delta")
    if vdelta is not None:
        vdelta = np.asarray(vdelta, dtype=np.float64)
        corr_yaw_vd = _safe_pearson(ryaw, vdelta) if n else None
        corr_toward_vd = _safe_pearson(toward, vdelta) if n else None
        vd_verdict, vd_fields = _credit_verdict(toward, vdelta, "value_delta")
        out.update({
            "corr_reward_walk_yaw_vs_value_delta": corr_yaw_vd,
            "corr_wz_toward_cmd_vs_value_delta": corr_toward_vd,
            "value_delta_mean_top_quartile_toward":
                vd_fields["value_delta_mean_top_quartile_toward"],
            "value_delta_mean_bottom_quartile_toward":
                vd_fields["value_delta_mean_bottom_quartile_toward"],
            "value_delta_std": vd_fields["value_delta_std"],
            "forward_verdict": vd_verdict,
        })
    return out


class RewardComponentCollector:
    """Per-tick collector for every ``reward_*`` scalar the env puts in
    ``info`` (sim_env builds ``info = {**parts, ...}`` — the components
    present vary tick to tick by mode/branch). Keys first seen mid-
    episode are zero-backfilled; keys absent on a tick get 0.0, so all
    arrays stay equal-length and per-tick means are well defined.

    ADDED 08-31 (turncap retention dig-in): the campaign refuted
    reward-magnitude retention at 1x AND 5x yaw pricing; the decisive
    open question is whether turning is even net-PROFITABLE per tick
    under the full training reward stack (yaw income vs drag/loadslip/
    course penalties while pivoting), which needs a component-level
    income account, not just the yaw channel. Pure python — unit-
    testable without torch/MuJoCo."""

    def __init__(self) -> None:
        self._cols: dict[str, list[float]] = {}
        self._n = 0

    def add(self, info: dict) -> None:
        for k, v in info.items():
            if not k.startswith("reward_"):
                continue
            try:
                fv = float(v)
            except (TypeError, ValueError):
                continue
            if k not in self._cols:
                self._cols[k] = [0.0] * self._n
            self._cols[k].append(fv)
        self._n += 1
        for col in self._cols.values():
            if len(col) < self._n:
                col.append(0.0)

    def arrays(self) -> dict[str, np.ndarray]:
        return {k: np.asarray(v, dtype=np.float64)
                for k, v in self._cols.items()}

    def means(self, idx: np.ndarray) -> dict[str, float]:
        """Mean of each component over the ``idx`` ticks (e.g. the
        scored window), sorted by |mean| descending so the biggest
        income/penalty lines read first."""
        if len(idx) == 0:
            return {}
        out = {k: float(np.mean(a[idx])) for k, a in
               self.arrays().items()}
        return dict(sorted(out.items(), key=lambda kv: -abs(kv[1])))


# ---------------------------------------------------------------------
# Rollout — dual-core GRU forward()-threaded value trace.
# ---------------------------------------------------------------------

def _zero_rnn_states(policy, n_envs: int = 1):
    import torch as th
    from sb3_contrib.common.recurrent.type_aliases import RNNStates

    h = policy.lstm_actor.hidden_size

    def z():
        return th.zeros(2, n_envs, h)

    return RNNStates((z(), z()), (z(), z()))


def load_dual_model(checkpoint: Path):
    """Load a checkpoint and require a DualGruActorCriticPolicy — this
    tool's RNNStates(pi, vf) threading is dual-core specific (separate
    per-core value heads gated the same way as the mean action)."""
    from .gru_policy import DualGruActorCriticPolicy, load_checkpoint_auto

    model = load_checkpoint_auto(checkpoint, device="cpu")
    if not isinstance(model.policy, DualGruActorCriticPolicy):
        raise SystemExit(
            "probe_yaw_credit requires a DualGruActorCriticPolicy "
            f"checkpoint (got {type(model.policy).__name__}); use "
            "policy.predict_values() directly for plain MLP/"
            "single-GRU checkpoints.")
    return model


def credit_rollout(*, model, cfg_set: list[str] | None, wz_cmd: float,
                    seed: int, episode_seconds: float,
                    gamma: float | None = None) -> dict:
    import torch as th

    policy = model.policy
    gamma = float(model.gamma if gamma is None else gamma)
    env = make_env(cfg_set, seed, episode_seconds, mode_onehot=True)
    obs, info = env.reset()
    traj = env._goal_traj
    n = len(traj.vx)
    hold_n = ramp_n = int(round(1.0 / env.dt))
    traj.vx[:] = 0.0
    traj.vy[:] = 0.0
    traj.wz[:] = wz_cmd
    traj.wz[:hold_n] = 0.0
    traj.wz[hold_n:hold_n + ramp_n] = np.linspace(0.0, wz_cmd, ramp_n)

    states = _zero_rnn_states(policy)
    episode_start = th.ones(1)
    policy.set_training_mode(False)

    step = 0
    rewards: list[float] = []
    values: list[float] = []
    wz_list: list[float] = []
    ryaw_list: list[float] = []
    mode_list: list[str] = []
    comps = RewardComponentCollector()
    fell = False
    with th.no_grad():
        while True:
            obs_t = th.as_tensor(obs[None]).float()
            actions_t, value_t, _logp, states = policy.forward(
                obs_t, states, episode_start, deterministic=True)
            action = actions_t.cpu().numpy()[0]
            action = np.clip(action, env.action_space.low,
                              env.action_space.high)
            values.append(float(value_t.item()))
            obs, r, term, trunc, info = env.step(action)
            rewards.append(float(r))
            wz_list.append(float(env._body_wz()))
            ryaw_list.append(float(info.get("reward_walk_yaw", 0.0)))
            comps.add(info)
            mode_list.append(info.get("goal_mode"))
            episode_start = th.zeros(1)
            step += 1
            if term:
                fell = True
            if term or trunc:
                break
        # Bootstrap: a real termination (fall/safety trip) has V=0 by
        # MDP convention (absorbing state); a truncation (episode
        # time limit, no failure) still has real future value — use
        # the critic's own estimate at the final obs, exactly like
        # SB3's own end-of-rollout truncation bootstrap.
        if trunc and not term:
            obs_t = th.as_tensor(obs[None]).float()
            _a, value_t, _lp, _st = policy.forward(
                obs_t, states, episode_start, deterministic=True)
            values.append(float(value_t.item()))
        else:
            values.append(0.0)
    env.close()
    td = td_residuals(rewards, values, gamma)
    value_delta = np.asarray(td) - np.asarray(rewards)

    scored = np.array([
        i for i in range(step)
        if i >= hold_n + ramp_n and mode_list[i] == "walk"
    ], dtype=int)
    masked = {
        "wz_cmd": wz_cmd,
        "wz": np.asarray(wz_list)[scored],
        "reward_walk_yaw": np.asarray(ryaw_list)[scored],
        "td_residual": td[scored],
        "value_delta": value_delta[scored],
    }
    summary = summarize(masked)
    # Income account over the scored window (08-31 retention dig-in):
    # is the behavior this checkpoint actually exhibits net-profitable
    # per tick under the training reward, and which components carry
    # it? Cross-checkpoint comparable (same reward cfg), unlike V(s).
    r_arr = np.asarray(rewards, dtype=np.float64)
    v_arr = np.asarray(values[:-1], dtype=np.float64)
    income = {
        "wz_med": (float(np.median(np.asarray(wz_list)[scored]))
                   if len(scored) else None),
        "reward_total_mean": (float(np.mean(r_arr[scored]))
                              if len(scored) else None),
        "value_mean": (float(np.mean(v_arr[scored]))
                       if len(scored) else None),
        "reward_components_mean": comps.means(scored),
    }
    return {
        "wz_cmd": wz_cmd, "seed": seed, "n_total_ticks": step,
        "gamma": gamma, "fell": fell, **summary, **income,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("checkpoint", type=Path)
    ap.add_argument("--cfg-set", action="append", default=None)
    ap.add_argument("--wz-cmds", default="0.25,-0.25")
    ap.add_argument("--seeds", default="0,1")
    ap.add_argument("--episode-seconds", type=float, default=15.0)
    ap.add_argument("--gamma", type=float, default=None)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    model = load_dual_model(args.checkpoint)
    wz_cmds = [float(x) for x in args.wz_cmds.split(",") if x.strip()]
    seeds = [int(x) for x in args.seeds.split(",") if x.strip()]

    results = []
    for wz_cmd in wz_cmds:
        for seed in seeds:
            res = credit_rollout(
                model=model, cfg_set=args.cfg_set, wz_cmd=wz_cmd,
                seed=seed, episode_seconds=args.episode_seconds,
                gamma=args.gamma)
            results.append(res)
            print(f"[probe_yaw_credit] wz_cmd={wz_cmd} seed={seed} "
                  f"n={res['n_ticks']} "
                  f"corr(yaw,td)={res['corr_reward_walk_yaw_vs_td']} "
                  f"corr(toward,td)={res['corr_wz_toward_cmd_vs_td']} "
                  f"-> {res['verdict']} | FORWARD-ONLY "
                  f"corr(toward,value_delta)="
                  f"{res.get('corr_wz_toward_cmd_vs_value_delta')} "
                  f"-> {res.get('forward_verdict')}")
            print(f"[probe_yaw_credit]   income: wz_med="
                  f"{res.get('wz_med')} reward_total_mean="
                  f"{res.get('reward_total_mean')} value_mean="
                  f"{res.get('value_mean')}")

    out = {"checkpoint": str(args.checkpoint), "results": results}
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(out, indent=2))
        print(f"[probe_yaw_credit] wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
