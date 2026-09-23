"""Walk-entry bank-handoff debt pricing (2026-09-23, standwalk).

Context (see `rl_docs/tracks/standwalk/STATUS.md` and
`CURRENT_TRUTHS.md` 2026-09-23 entries for the full saga): the
composed-session rise->walk handoff hands the walk specialist a
carried-over pose that sometimes differs substantially (in height and
joint angle) from the specialist's own ordinary `plant` reset --
`eval_modeseq.py --dump-seg-qpos` + `analyze_seg_qpos.py` show the
episodes that go on to FALL have an entry-vs-cold-reset
`height_err_delta_mm` roughly 2x the episodes that recover fine (fell
median ~35-40mm vs ok median ~15-24mm; `q_deg_max_delta` fell median
~35-40deg vs ok ~24deg). Three prior fix SHAPES all failed to move
this gap: exposure-fraction blending the reset distribution
(`goal.walk_entry_bank`, position-only, 3/3 FAIL across doses),
restoring real handoff velocity too (`goal.bank_qvel_restore`, 2/2
FAIL), and giving the rare bank-drawn episodes their own undiluted PPO
minibatch (`goal_mode_batch_split_walk_start_kind`, FAIL, falls
byte-identical 9/30 to every prior sibling). All three reshaped the
RESET distribution or the GRADIENT batching; none of them changed
what the specialist is actually REWARDED for once it lands in that
state. This module is the remaining named lever: price the exact
off-manifold signature `analyze_seg_qpos.py` uses to separate fell
from ok episodes DIRECTLY in the reward, so the specialist has an
explicit, differentiable incentive to close the gap quickly after a
genuine bank-drawn handoff, instead of only ever being rewarded for
forward progress regardless of how far off-manifold its current pose
still is.

Contract (default OFF / bit-exact):
  - `goal.walk_bank_entry_debt_scale` (default 0.0): reward units per
    meter of `|height_err|` beyond the safe band, once the episode is
    a genuine `start_kind=="bank"` walk draw. <=0 is a hard no-op --
    the function returns `reward` unchanged and never touches `parts`.
  - Only ever fires on `goal.mode=="walk"` episodes whose
    `start_kind_of(traj)=="bank"` (a real `goal.walk_entry_bank` draw,
    the same label `goal_mode_batch_split.py`'s walk-start_kind split
    already trusts) -- an ordinary `plant` walk episode is a no-op
    even with the flag armed, so a normal training run's reward
    composition is unaffected by simply turning this on.
  - `goal.walk_bank_entry_debt_window_s` (default 1.5s): the penalty
    only applies for this many seconds after `reset()` (using
    `control.hz` to convert to ticks) -- it prices the HANDOFF, not
    ordinary walking, so a specialist that has already stabilized
    stops paying it.
  - `goal.walk_bank_entry_debt_safe_mm` (default 20.0mm): the band
    inside which no penalty applies (roughly the `ok`-episode
    `height_err_delta_mm` scale from the diagnostic) -- only the
    EXCESS beyond this band is priced, and it is bounded per tick
    (capped at a 100mm-equivalent debt) so a single bad tick can't
    blow up the return.
"""
from __future__ import annotations

from rl_move.config import cfg_get
from rl_move.env import start_kind_of


def walk_bank_entry_debt_reward(env, goal, h_err, parts, reward):
    scale = float(cfg_get(env.cfg, "goal", "walk_bank_entry_debt_scale",
                           default=0.0))
    if scale <= 0.0 or goal is None or h_err is None:
        return reward
    if getattr(goal, "mode", "") != "walk":
        return reward
    traj = getattr(env, "_goal_traj", None)
    if traj is None or start_kind_of(traj) != "bank":
        return reward
    window_s = float(cfg_get(env.cfg, "goal",
                              "walk_bank_entry_debt_window_s", default=1.5))
    hz = float(cfg_get(env.cfg, "control", "hz", default=50.0))
    window_steps = max(1, int(round(window_s * hz)))
    if int(getattr(env, "_step_i", 0)) > window_steps:
        return reward
    safe_mm = float(cfg_get(env.cfg, "goal",
                             "walk_bank_entry_debt_safe_mm", default=20.0))
    debt_mm = max(0.0, abs(float(h_err)) * 1000.0 - safe_mm)
    debt_mm = min(debt_mm, 100.0)
    penalty = scale * (debt_mm / 1000.0)
    reward -= penalty
    parts["reward_bank_entry_debt"] = -penalty
    return reward
