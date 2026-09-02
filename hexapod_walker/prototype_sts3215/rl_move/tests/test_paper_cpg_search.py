"""Fast checks for the Berkeley-style CPG gait search runner."""
from __future__ import annotations

import sys
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT, ROOT / "linux_control", ROOT / "linux_control" / "urt2_setup"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from rl_move.sim.paper_cpg_search import (  # noqa: E402
    aggregate_reality_trials,
    score_rollouts,
)
from rl_move.sim.domain_rand import DomainRandomizer, G0  # noqa: E402
from hexapod_core.se2_foot_gait import SE2FootGait  # noqa: E402


def test_se2_gait_outputs_canonical_robot_absolute_knees():
    g = SE2FootGait(gait="tetrapod", vx=0.0, vy=0.0, omega=0.0)
    g.sync_plant_stance(20.0, 80.0)
    q = g.desired_deg(0.0)
    for leg in range(6):
        hip = q[3 * leg + 1]
        knee = q[3 * leg + 2]
        assert abs(hip - 20.0) < 1e-6
        assert abs(knee - 80.0) < 1e-6


def test_score_prefers_progress_low_slip_no_fall():
    base = {
        "progress_frac": 0.95,
        "cross_frac": 0.05,
        "slip_per_m": 0.35,
        "roll_peak_deg": 3.0,
        "pitch_peak_deg": 3.0,
        "current_p95_a": 1.0,
        "terminated": "",
        "command_scale": 1.0,
    }
    slippery = dict(base, slip_per_m=3.0)
    wrong_way = dict(base, progress_frac=-0.25, cross_frac=1.0)
    fallen = dict(base, terminated="roll")

    good_s = score_rollouts([base])["score"]
    slip_s = score_rollouts([slippery])["score"]
    wrong_s = score_rollouts([wrong_way])["score"]
    fall_s = score_rollouts([fallen])["score"]

    assert good_s > slip_s
    assert good_s > wrong_s
    assert good_s > fall_s


def test_reality_panel_interpolates_mean_and_worst_score():
    records = [
        {
            "params": {"gait": "tetrapod"},
            "score": score,
            "summary": {
                "falls": falls,
                "progress_frac_mean": progress,
                "slip_per_m_mean": 0.5,
            },
        }
        for score, falls, progress in ((1.0, 0, 0.9), (-1.0, 1, 0.3))
    ]

    mean = aggregate_reality_trials(records, risk_weight=0.0)
    middle = aggregate_reality_trials(records, risk_weight=0.5)
    worst = aggregate_reality_trials(records, risk_weight=1.0)

    assert mean["score"] == 0.0
    assert middle["score"] == -0.5
    assert worst["score"] == -1.0
    assert middle["summary"]["falls"] == 1
    assert middle["summary"]["progress_frac_mean"] == 0.6


def test_fixed_ground_slope_is_applied_without_randomization():
    dr = DomainRandomizer(scale=0.0)
    dr.set_ground_slope(tilt_deg=1.5, downhill_azimuth_deg=90.0)

    episode = dr.sample(np.random.default_rng(3))

    assert abs(episode.gravity_vec[0]) < 1e-12
    assert episode.gravity_vec[1] > 0.0
    assert math.isclose(np.linalg.norm(episode.gravity_vec), G0)
    measured = math.degrees(math.acos(-episode.gravity_vec[2] / G0))
    assert math.isclose(measured, 1.5, abs_tol=1e-10)
