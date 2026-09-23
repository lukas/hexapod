"""Regression test (2026-09-23, cw-stand50hz-mlp-dr06-fromdr05-
hardstartcorr): eval_checkpoint.py's --cfg-set resolver used a plain
``key.split(".", 1)``, which raised ValueError on a dot-less key (e.g.
a stray ``--cfg-set dr_scale=0.6`` that should have been the separate
``--dr-scale`` CLI flag). train_ppo_sim.py's _build_env/_resolved_cfg
already TOLERATE a dot-less key (it becomes a harmless top-level cfg
entry, a no-op) -- eval must replay the exact same resolved cfg a run
actually trained under, not a stricter parser that crashes on it,
or gate-eval of an otherwise-fine checkpoint is blocked entirely.

Fast/mechanics-only per RESEARCH_RULES "Tests": no checkpoint load, no
rollout, no artifacts -- duplicates the exact resolver block eval_
checkpoint.py's main() runs (same style as
test_eval_cmd_suite_cfg_parse.py's
test_eval_cmd_suite_cfg_dict_matches_shared_parser) and checks it
against a real config.yaml base, plus a source-text check that the
shipped file uses the tolerant multi-level walk, not the old
single-split.
"""
from __future__ import annotations

from pathlib import Path

from rl_move.config import load_config
from rl_move.sim.cfg_set import _parse_cfg_set

ROOT = Path(__file__).resolve().parents[2]


def _resolve(cfg_set: list[str]) -> dict:
    """Mirrors the exact block in eval_checkpoint.py's main()."""
    cfg = load_config()
    for key, parsed in _parse_cfg_set(cfg_set).items():
        node = cfg
        *path, leaf = key.split(".")
        for k in path:
            node = node.setdefault(k, {})
        node[leaf] = parsed
    return cfg


def test_dotless_key_is_a_harmless_top_level_noop():
    cfg = _resolve(["dr_scale=0.6", "dr.hard_start_correlate_frac=1.0"])
    assert cfg["dr_scale"] == 0.6
    # the real, namespaced key still resolves normally alongside it
    assert cfg["dr"]["hard_start_correlate_frac"] == 1.0


def test_dotted_single_level_key_unchanged():
    cfg = _resolve(["reward.k_action=0.005", "goal.rise_height_mm=[79,87]"])
    assert cfg["reward"]["k_action"] == 0.005
    assert cfg["goal"]["rise_height_mm"] == [79, 87]


def test_eval_checkpoint_uses_the_tolerant_multilevel_walk():
    src = (ROOT / "rl_move" / "sim" / "eval_checkpoint.py").read_text()
    assert 'sect, name = key.split(".", 1)' not in src, (
        "eval_checkpoint.py must not use the strict single-split "
        "cfg-set resolver -- it raises ValueError on a dot-less key "
        "that train_ppo_sim.py's _build_env/_resolved_cfg tolerate "
        "as a no-op, blocking gate-eval of a run that trained fine")
    assert "*path, leaf = key.split" in src
