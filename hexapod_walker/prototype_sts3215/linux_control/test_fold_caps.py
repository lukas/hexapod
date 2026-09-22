"""Per-robot fold caps: the baked STEP frames ask for hips -78 / knees 148; hexapod2 stops near -55 / 126.

2026-09-22: commanding past the stop while loaded was an 8.2 A fight (reversed sit parked tall);
with the caps the same reversed STEP completes in 5.4 s at 0.16 A peak.  The cap is a clamp on
every commanded frame, keyed by hostname, env-overridable; other robots keep the frames as baked."""
import importlib
import json
from pathlib import Path


def _reload_with_host(monkeypatch, host):
    import api.standup as st
    monkeypatch.setattr("socket.gethostname", lambda: host)
    monkeypatch.delenv("HEXAPOD_HIP_FOLD_CAP_DEG", raising=False)
    monkeypatch.delenv("HEXAPOD_KNEE_FOLD_CAP_DEG", raising=False)
    return importlib.reload(st)


def test_hexapod2_caps_clamp_the_step_fold(monkeypatch):
    st = _reload_with_host(monkeypatch, "hexapod2")
    assert (st.HIP_FOLD_CAP_DEG, st.KNEE_FOLD_CAP_DEG) == (-52.0, 125.0)
    kfs = json.loads((Path(st.__file__).parents[1] / "standup_modes.json").read_text())["modes"]["step"]["keyframes"]
    hips = [q for k in kfs for i, q in enumerate(k["q_deg"]) if i % 3 == 1]
    knees = [q for k in kfs for i, q in enumerate(k["q_deg"]) if i % 3 == 2]
    assert min(hips) < st.HIP_FOLD_CAP_DEG and max(knees) > st.KNEE_FOLD_CAP_DEG, "the baked frames overshoot this robot"
    capped = [max(float(v), st.HIP_FOLD_CAP_DEG) if i % 3 == 1 else (min(float(v), st.KNEE_FOLD_CAP_DEG) if i % 3 == 2 else float(v))
              for k in kfs for i, v in enumerate(k["q_deg"])]
    assert min(capped[1::3]) == -52.0 and max(capped[2::3]) == 125.0


def test_other_robots_keep_the_baked_frames(monkeypatch):
    st = _reload_with_host(monkeypatch, "hexapod")
    assert st.HIP_FOLD_CAP_DEG <= -78.0 and st.KNEE_FOLD_CAP_DEG >= 148.0


def test_env_overrides_the_cap(monkeypatch):
    import api.standup as st
    monkeypatch.setattr("socket.gethostname", lambda: "hexapod2")
    monkeypatch.setenv("HEXAPOD_KNEE_FOLD_CAP_DEG", "130")
    st = importlib.reload(st)
    assert st.KNEE_FOLD_CAP_DEG == 130.0
    monkeypatch.delenv("HEXAPOD_KNEE_FOLD_CAP_DEG")
    importlib.reload(st)
