"""goal.lower_ramp_s cfg override (2026-10-02, walkcurr lower-role
over_current forensics -- see goal_task.py's own comment at the
assignment site): mechanics-only check that (a) the default is
unchanged (bit-exact legacy 5.0s) when the key is absent, and (b) the
override actually reaches ``GoalGenerator.lower_ramp_s`` when set --
mirrors ``rise_ramp_s``'s own existing cfg-precedence contract one
line above it, just without the full env/PPO probe weight."""
from rl_move.config import load_config
from rl_move.sim.goal_task import GoalGenerator


def test_lower_ramp_s_default_bit_exact():
    cfg = load_config()
    gen = GoalGenerator(cfg)
    assert gen.lower_ramp_s == 5.0


def test_lower_ramp_s_cfg_override_applies():
    cfg = load_config()
    cfg.setdefault("goal", {})["lower_ramp_s"] = 9.0
    gen = GoalGenerator(cfg)
    assert gen.lower_ramp_s == 9.0
