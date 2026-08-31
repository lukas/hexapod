"""Unit tests for probe_mirror_turn_authority's pure classification
logic (no MuJoCo/torch needed — those paths are exercised manually,
see the tool's own docstring for the real invocation)."""
from rl_move.sim.probe_mirror_turn_authority import FAIL_FLOOR, PASS_FLOOR


def _classify(naked_med, mirror_med, wz_cmd):
    naked_frozen = abs(naked_med) < FAIL_FLOOR
    same_sign = mirror_med * wz_cmd > 0
    clears_fail = same_sign and abs(mirror_med) >= FAIL_FLOOR
    clears_pass = same_sign and abs(mirror_med) >= PASS_FLOOR
    return naked_frozen, clears_fail, clears_pass


def test_escape_classification_matches_measured_dualbc5_turncap_read():
    """Locks the actual 08-31 measured numbers
    (logs/ckpt_eval/mirror_turn_authority_dualbc5_turncap.json):
    naked is frozen (<0.03) on +0.25, mirror escapes past 0.03 on the
    SAME sign (but below the 0.08 PASS bar) — a genuine, if partial,
    zero-training escape route this campaign's 8 RL mechanism classes
    never produced."""
    naked_frozen, clears_fail, clears_pass = _classify(
        naked_med=-0.00007, mirror_med=0.058, wz_cmd=0.25)
    assert naked_frozen
    assert clears_fail
    assert not clears_pass


def test_escape_classification_rejects_opposite_sign():
    """A same-magnitude but OPPOSITE-sign mirror read must not count
    as an escape (that would be tracking the wrong direction)."""
    naked_frozen, clears_fail, clears_pass = _classify(
        naked_med=0.001, mirror_med=-0.058, wz_cmd=0.25)
    assert naked_frozen
    assert not clears_fail
    assert not clears_pass


def test_escape_classification_requires_naked_frozen_first():
    """If naked already tracks (>=0.03), it is not the frozen sign —
    do not credit mirror with 'fixing' something that was not broken."""
    naked_frozen, clears_fail, clears_pass = _classify(
        naked_med=0.05, mirror_med=0.09, wz_cmd=0.25)
    assert not naked_frozen
