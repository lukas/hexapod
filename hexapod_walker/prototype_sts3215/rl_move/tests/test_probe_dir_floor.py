"""Tests for probe_dir_floor.py's 09-05 heading-resample extension
(standwalk, closing the mlcontprice8 literal-DONE-gate FALL): confirms
(a) the legacy fixed-heading floor (resample-s=0, the default) is
untouched -- zero resamples, output unchanged in shape; (b) turning
resampling on actually redraws the commanded heading at least once
over a multi-segment rollout and reports it. Short env-integration
smoke test (few seconds of sim), not a full 60s floor read."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sim"))
import probe_dir_floor as pdf  # noqa: E402


def _run(tmp_path, extra_args, seconds=6.0, seed=0):
    out_path = tmp_path / "out.json"
    argv = [
        "probe_dir_floor", "--model-source", "mesh", "--hz", "100",
        "--vx", "0.08", "--seconds", str(seconds), "--seed", str(seed),
        "--json-out", str(out_path),
    ] + extra_args
    old_argv = sys.argv
    sys.argv = argv
    try:
        pdf.main()
    finally:
        sys.argv = old_argv
    return json.loads(out_path.read_text())


def test_default_resample_off_is_legacy_shape(tmp_path):
    out = _run(tmp_path, [])
    assert out["resample_s"] == 0.0
    assert out["n_resamples"] == 0
    assert out["fell"] is False
    assert out["tick_dir_err_med_deg"] is not None


def test_resample_on_redraws_heading(tmp_path):
    out = _run(tmp_path, [
        "--resample-s", "1.0", "--resample-jitter", "0.0",
        "--heading-max-deg", "180", "--blend-s", "1.0",
    ], seconds=6.0)
    assert out["resample_s"] == 1.0
    # 6s rollout, 1s segments, zero jitter -> ~5-6 resamples.
    assert out["n_resamples"] >= 4
    assert out["fell"] is False


def test_resample_zero_span_never_fires(tmp_path):
    # resample_s == 0.0 must short-circuit to "off" (inf next-time),
    # not attempt a zero-length jitter draw.
    out = _run(tmp_path, [
        "--resample-s", "0.0", "--heading-max-deg", "180",
    ], seconds=4.0)
    assert out["n_resamples"] == 0
