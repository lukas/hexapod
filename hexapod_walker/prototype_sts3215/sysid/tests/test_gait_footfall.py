"""sysid.gait_metrics --footfall on a synthetic tripod: mechanics only, no files."""
import numpy as np

from sysid import gait_metrics as gm

HZ = 50.0
PERIOD_S = 1.5


def _tripod_csv(seconds=6.0, lift_deg=12.0, weak_lift_deg=None):
    """Stand pose [0, 20, 80] with a tripod gait: legs 1/3/5 swing in the first
    half of each cycle, 0/2/4 in the second. Swing = femur up (negative) by
    lift_deg for 0.3 of the period, with a coxa sweep; stance = coxa sweeping back."""
    n = int(seconds * HZ)
    t = np.arange(n) / HZ
    q = np.tile([0.0, 20.0, 80.0], 6)[None, :].repeat(n, 0).astype(float)
    ph = (t % PERIOD_S) / PERIOD_S
    for leg in range(6):
        strong = leg % 2 == 1
        p = (ph if strong else (ph + 0.5) % 1.0)
        swing = p < 0.3
        lift = lift_deg if (strong or weak_lift_deg is None) else weak_lift_deg
        femur = np.where(swing, 20.0 - lift * np.sin(np.pi * p / 0.3), 20.0)
        coxa = np.where(swing, -10 + 20 * p / 0.3, 10 - 20 * (p - 0.3) / 0.7)
        q[:, 3 * leg + 1] = femur
        q[:, 3 * leg] = coxa
    d = {"t_s": t, "vx_ref_mps": np.full(n, 0.1), "phase": np.array(["walk"] * n)}
    for j in range(18):
        d[f"q{j}_deg"] = q[:, j]
        d[f"cmd{j}_deg"] = q[:, j]
    return d


def test_tripod_duty_and_groups():
    f = gm.footfall(_tripod_csv(), thr_mm=5.0)
    duties = [L["duty"] for L in f["legs"]]
    # 30 % swing per cycle -> duty ~0.7 for every leg
    assert all(0.6 < x < 0.8 for x in duties), duties
    assert all(L["swings_per_s"] is not None and 0.55 < L["swings_per_s"] < 0.8 for L in f["legs"])
    # never fewer than three feet down in an ideal tripod
    assert f["frac_lt3_feet"] == 0.0
    # 0/2/4 and 1/3/5 alternate: their swings never overlap, and between them
    # all six feet are down (40 % of the cycle by construction, more once the
    # shallow ends of each sine lift fall under the contact threshold)
    assert 0.3 < f["frac_all6_down"] < 0.65


def test_weak_tripod_shows_as_lower_lift():
    f = gm.footfall(_tripod_csv(lift_deg=14.0, weak_lift_deg=6.0), thr_mm=5.0)
    lifts = [L["lift_mm"] for L in f["legs"]]
    weak = np.mean([lifts[i] for i in (0, 2, 4)])
    strong = np.mean([lifts[i] for i in (1, 3, 5)])
    assert strong > 1.6 * weak, lifts


def test_diagram_and_cmd_source():
    d = _tripod_csv(seconds=3.0)
    diag = gm.footfall_diagram(d, thr_mm=5.0)
    assert diag.count("\n") == 6 and "#" in diag and "." in diag
    f = gm.footfall(d, thr_mm=5.0, use_cmd=True)
    assert f["source"] == "cmd" and len(f["legs"]) == 6


def test_body_speed_sign_follows_vx_ref():
    d = _tripod_csv()
    f_fwd = gm.footfall(d, thr_mm=5.0)
    d["vx_ref_mps"] = -d["vx_ref_mps"]
    f_back = gm.footfall(d, thr_mm=5.0)
    assert f_fwd["body_speed_from_feet_mm_s"] == f_back["body_speed_from_feet_mm_s"]
    assert np.sign(f_fwd["body_speed_along_cmd_mm_s"]) == -np.sign(f_back["body_speed_along_cmd_mm_s"])
