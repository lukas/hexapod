"""Mechanics-only tests for the currentcap29 flat-only probe cfg
builder (walkcurr, 2026-09-17). No rollouts, no rankings -- just
checks the arg list is well-formed and actually forces flat-only,
per RESEARCH_RULES "Tests".
"""
from rl_move.sim.probe_currentcap29_flatonly import (
    BASE_CFG_ARGS,
    FLATONLY_OVERRIDE_ARGS,
    build_argv,
    build_cfg_args,
)


def test_cfg_args_are_key_value_strings_no_dupes():
    args = build_cfg_args()
    assert args, "cfg arg list must not be empty"
    keys = []
    for kv in args:
        assert isinstance(kv, str) and "=" in kv, kv
        key = kv.split("=", 1)[0]
        keys.append(key)
    # BASE has an intentional rise_flat_frac/rise_partial_frac pair
    # that FLATONLY_OVERRIDE_ARGS re-specifies afterwards -- that's the
    # ONLY allowed duplicate; nothing else should repeat.
    dupes = {k for k in keys if keys.count(k) > 1}
    assert dupes == {"goal.rise_flat_frac", "goal.rise_partial_frac"}, dupes


def test_flatonly_override_wins_last():
    args = build_cfg_args()
    # last occurrence of each overridden key must be the flat-only value
    flat_idx = [i for i, kv in enumerate(args) if kv.startswith("goal.rise_flat_frac=")]
    partial_idx = [i for i, kv in enumerate(args) if kv.startswith("goal.rise_partial_frac=")]
    assert args[flat_idx[-1]] == "goal.rise_flat_frac=1.0"
    assert args[partial_idx[-1]] == "goal.rise_partial_frac=0"


def test_model_source_and_control_hz_present():
    # The exact bug this module exists to prevent: a probe missing
    # these two silently evaluates on the wrong physics family/rate.
    args = set(build_cfg_args())
    assert "env.model_source=mesh_mjx" in args
    assert "control.hz=50" in args


def test_build_argv_shape():
    argv = build_argv("some/ckpt.zip", out="logs/ckpt_eval/x_flatonly_det",
                       dr_scale=0.0, stochastic=False)
    assert argv[0] == "some/ckpt.zip"
    assert "--stochastic" not in argv
    assert "--modes" in argv
    modes_i = argv.index("--modes")
    assert argv[modes_i + 1:modes_i + 4] == ["hold", "rise", "lower"]
    assert "--cfg-set" in argv
    # every FLATONLY_OVERRIDE_ARGS entry must appear as its own --cfg-set value
    for kv in FLATONLY_OVERRIDE_ARGS:
        assert kv in argv

    argv_sto = build_argv("some/ckpt.zip", out="logs/ckpt_eval/x_flatonly_sto",
                           stochastic=True)
    assert argv_sto[-1] == "--stochastic"


def test_base_cfg_args_is_a_flat_list_of_strings():
    assert isinstance(BASE_CFG_ARGS, list)
    assert all(isinstance(x, str) for x in BASE_CFG_ARGS)
