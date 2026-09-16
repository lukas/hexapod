"""First-principles posture prices of the balance env's _step_finish:
support margin, load evenness, torque headroom debt, action-rate/stance-
contact/stance-clearance/flag-leg shaping, terminal end-posture pricing
and the terminal bleed settlement; moved verbatim out of sim_env.py.
"""
from __future__ import annotations

import numpy as np

from rl_move.config import cfg_get

from .balance_helpers import support_margin_m, torque_headroom_debt_step


def posture_support_load_headroom_reward(env, goal, parts, reward):
    """Support-margin, load-even and torque-headroom prices; moved verbatim
    from SimHexapodBalanceEnv._step_finish.
    """
    # --- First-principles posture terms (operator 08-08 ~20:45Z,
    # default OFF). WHY a waving leg is bad: smaller support polygon
    # (tips), load concentration (hot knees), wasted hold torque.
    # Static-hold pricing was measured CORRECT (hip 0.149 Nm -> 0.179 A,
    # actuator carries full gravity torque; diagnosis 08-08 cycle 12):
    # the defect is that the LINEAR current charge is invariant to load
    # distribution, so concentration is free. These two GLOBAL terms
    # price the physics directly, in every mode (declared routing:
    # GLOBAL - they encode "don't tip / don't concentrate heat", not
    # gait morphology). The unload target leg is skipped like the
    # other stance terms.
    k_margin = float(cfg_get(env.cfg, "reward", "k_support_margin",
                             default=0.0))
    k_even = float(cfg_get(env.cfg, "reward", "k_load_even",
                           default=0.0))
    if (k_margin > 0.0 or k_even > 0.0):
        skip = int(goal.unload_leg) if (
            goal is not None and goal.unload_leg is not None) else -1
        forces, feet_xy = [], []
        for i in range(6):
            if i == skip or env._touch_adr[i] < 0:
                continue
            f = max(float(env.data.sensordata[env._touch_adr[i]]), 0.0)
            forces.append(f)
            if f > 0.5 and env._pad_bids[i] >= 0:
                feet_xy.append(env.data.xpos[env._pad_bids[i], :2])
        if k_margin > 0.0 and len(feet_xy) >= 3:
            # Reward CoM depth inside the support polygon, saturating
            # at 40 mm: centered stances earn the cap, near-edge or
            # outside-CoM poses earn ~0/negative. Belly rest (<3 foot
            # contacts, chassis supported) is exempt by the gate.
            m = support_margin_m(np.asarray(feet_xy),
                                 env.data.subtree_com[0, :2])
            r_margin = k_margin * float(np.clip(m, -0.04, 0.04)) / 0.04
            parts["reward_support_margin"] = r_margin
            reward += r_margin
        ftot = float(np.sum(forces))
        if k_even > 0.0 and ftot > 1.0:
            # Load concentration: Herfindahl index of foot normal
            # forces. Even 6-leg load = 1/6 (charge 0); everything on
            # one foot = 1 (max charge). Dense, mode-independent.
            fr = np.asarray(forces) / ftot
            hhi = float(np.sum(fr ** 2))
            r_even = -k_even * (hhi - 1.0 / len(forces))
            parts["reward_load_even"] = r_even
            reward += r_even
    # Per-actuator torque-HEADROOM debt (standwalk track, 2026-09-11 —
    # the structural mechanism named after both `k_current_hot` (dose
    # bracket b23k12/k6/b23k36) and `k_load_even` (dose bracket 2/8/
    # 16/32) closed short of a clean PASS on the b23k12 flat-start
    # rise stall-fight). Root-cause chain (09-11 ~08:0x DIG-IN,
    # CURRENT_TRUTHS.md): a SINGLE femur-row servo pins at torque
    # saturation (raw_current's own 2.2 N-m x 1.2 A/N-m = 2.64 A rail,
    # see the raw_current comment above) for up to 23% of the episode
    # while the existing per-tick current_hot price stays a flat,
    # MEMORYLESS quadratic on instantaneous current (~1.4/tick at
    # this lineage's dose) — cheaper than the ~3.4/tick rise/hold/
    # finish income, so fighting through isometrically instead of
    # momentarily unloading is the reward optimum. Raising the FLAT
    # per-tick price alone (b23k36, ~4.2/tick, ABOVE that income) did
    # NOT move the residual at all (over_current pinned at 1/12
    # across a 3.5x price range) — so the missing axis is DURATION,
    # not magnitude: this term is a per-actuator leaky integrator
    # ("debt") that only grows while a servo dwells inside a red zone
    # just below the physical torque-saturation current, decaying
    # back to 0 once it unloads, then prices the debt QUADRATICALLY.
    # A brief transient spike (a few ticks) barely moves the debt and
    # costs almost nothing (no new tax on ordinary current use
    # anywhere else in the episode); a SUSTAINED stall-fight compounds
    # every tick it continues, so the charge escalates past whatever
    # a flat per-tick price could reach for the exact pathology named
    # above, without needing a heavier tax on brief/harmless spikes.
    # Dense, mode-independent (declared routing: GLOBAL, same as
    # k_current_hot/k_load_even — "don't let any one actuator stall
    # near its ceiling", not gait morphology). Bit-exact OFF by
    # default: the debt array is only allocated/updated when enabled.
    # Enable: --cfg-set reward.k_torque_headroom=<k>.
    k_headroom = float(cfg_get(env.cfg, "reward", "k_torque_headroom",
                                default=0.0))
    if k_headroom > 0.0 and env._state.servo_current is not None:
        cur = np.abs(env._state.servo_current)
        if (getattr(env, "_torque_debt", None) is None
                or env._torque_debt.shape != cur.shape):
            env._torque_debt = np.zeros_like(cur)
        alpha_d = min(max(env.dt, 0.0), 1.0)
        env._torque_debt = torque_headroom_debt_step(
            env._torque_debt, cur, 2.64, 0.3, alpha_d)
        r_headroom = -k_headroom * float(np.sum(env._torque_debt ** 2))
        parts["reward_torque_headroom"] = r_headroom
        parts["torque_headroom_debt_max"] = float(
            np.max(env._torque_debt))
        reward += r_headroom
    return reward
