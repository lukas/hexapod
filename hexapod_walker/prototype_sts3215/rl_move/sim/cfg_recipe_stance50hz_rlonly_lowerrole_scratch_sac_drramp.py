"""Canonical `cw-stance50hz-rlonly-lowerrole-scratch-sac-{s0,s1}-drramp-
acq1` cfg-set list, versioned in code -- same rationale/precedent as
`cfg_recipe_walk50hz_rlonly_v2.py` / `cfg_recipe_walk50hz_slew_smooth_
s0.py` (walkcurr): this is the first `lower`-role checkpoint in the
`rl_only` lineage to clear its own acquisition gate under trained DR
(walkcurr/STATUS.md 2026-09-24 ~11:5x, PASS 2/2 seeds), registered by
`todaypolicy` the same cycle as a new lifecycle-composition candidate
-- a hand-retyped cfg-set list is exactly the mistake this project's
prior versioned-recipe modules already exist to prevent.

Verbatim from the recorded launch command (``ops.sh entry
cw-stance50hz-rlonly-lowerrole-scratch-sac-s0-drramp-acq1``),
--cfg-set values only (training-only flags -- --steps, --algo,
--seed, --notes, --defer-final-artifacts, --goal-mix, etc. -- dropped;
they don't affect an eval env's construction). ``env.dr_stage_ramp_
steps=4000000`` is EXCLUDED per the same always-off-at-eval convention
as the sibling recipe modules: this eval harness always builds its
envs with ``randomize=False`` (dr-scale forced to 0), and
`sim_env.py` hard-fails if a >0 ramp-steps value is set without an
active `DomainRandomizer` (the exact bug walkcurr's own drramp gate
pass tripped and fixed in `orchestrator/pod_eval.py` this same cycle)
-- the ramp fraction is moot with DR off regardless.

This is a MECHANICS-ONLY module (a literal arg list) -- it does not
rank rollouts and carries no reward/behavior opinion.
"""
from __future__ import annotations

# Order matters for --cfg-set (later duplicate keys win). Verbatim
# order from the training command (ops.sh entry cw-stance50hz-rlonly-
# lowerrole-scratch-sac-s0-drramp-acq1), minus env.dr_stage_ramp_steps
# (excluded, see module docstring). No obs.*/goal.joint_action_bias_*/
# safety.max_current_a overrides were set by this launch command --
# unlike the sibling `probe_currentcap29_flatonly` lineage, this
# recipe relies on config.yaml's own current defaults for those
# fields, so this list must NOT borrow that module's BASE_CFG_ARGS
# wholesale (verified against the ledger's own extra_args, not
# assumed from lineage similarity).
CFG_ARGS: list[str] = [
    "env.model_source=mesh_mjx",
    "control.hz=50",
    "safety.max_delta_q_deg=0.75",
    "actions.max_height_mm=88",
    "goal.rise_height_mm=[79,87]",
    "goal.rise_ramp_s=6.0",
    "goal.rise_hold_min_s=0.5",
    "reward.rise_score_income=1.0",
    "reward.rise_score_strip_pen=1.0",
    "reward.rise_posture_gate=1.0",
    "reward.rise_income_prog_gate=1.0",
    "reward.rise_finish_gate_signed=1.0",
    "reward.hold_still_gate=1.0",
    "reward.hold_flag_fade=1.0",
    "reward.k_current_hot=1.0",
    "reward.current_hot_a=2.0",
    "reward.term_cost_per_remaining_s=3.0",
    "reward.term_cost_max=60.0",
    "reward.hold_feet_load=1.0",
    "reward.hold_feet_load_min=1.0",
    "safety.hold_max_height_drop_mm=15",
    "safety.hold_height_grace_s=0.5",
    "safety.hold_min_load_terminate_s=1.0",
    "safety.hold_min_load_terminate_n=0.3",
    "safety.hold_min_load_terminate_grace_s=1.0",
]
