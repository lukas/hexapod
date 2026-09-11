"""``_save_video`` must never collide on dotted (pinned-speed/heading) labels.

Found 2026-09-11 (speed track acquisition triage): ``_save_video`` used
``Path.with_suffix(".mp4")`` to add its extension. For a bare name built
from an f-string like ``f"walk@{s:.3f}_{tag}_{k}"`` (the pinned-speed and
pinned-heading panels' filename convention), ``Path.with_suffix`` treats
everything after the LAST '.' as the suffix to replace -- so
``walk@0.060_det_0`` collapsed to ``walk@0.mp4``, silently overwriting
every speed/heading/tag/k video in one panel call with only the
last-written one surviving. This test pins the fix (``_with_ext``: plain
string append, never ``Path.with_suffix``) so it cannot regress silently.
"""
from __future__ import annotations

from pathlib import Path

from rl_move.sim.eval_checkpoint import _with_ext


def test_with_ext_preserves_dotted_pinned_speed_labels(tmp_path):
    # The exact filename shape pinned_speed_panel/pinned_heading_panel
    # build: f"walk@{s:.3f}_{tag}_{k}" -- contains a '.' that
    # Path.with_suffix would misparse as an extension separator.
    base = tmp_path / "walk@0.060_det_0"
    assert _with_ext(base, ".mp4") == tmp_path / "walk@0.060_det_0.mp4"
    assert _with_ext(base, ".png") == tmp_path / "walk@0.060_det_0.png"


def test_with_ext_distinguishes_every_pin_in_a_panel(tmp_path):
    # Four pins x two tags must produce EIGHT distinct file paths, not
    # collapse onto one (the exact bug: all 8 previously mapped to the
    # same "walk@0.mp4").
    names = {
        _with_ext(tmp_path / f"walk@{s:.3f}_{tag}_0", ".mp4")
        for s in (0.06, 0.08, 0.10, 0.12)
        for tag in ("det", "sto")
    }
    assert len(names) == 8


def test_with_ext_still_works_for_plain_dot_free_names(tmp_path):
    # Standard mode/tag/k names (no dot) must keep working exactly as
    # before -- this is a strict widening, not a behavior change for the
    # common case.
    base = tmp_path / "walk_det_0"
    assert _with_ext(base, ".mp4") == tmp_path / "walk_det_0.mp4"
