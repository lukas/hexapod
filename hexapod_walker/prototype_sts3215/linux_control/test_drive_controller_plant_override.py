"""`PLANT hip knee` overrides the scripted gaits' stance (sim2real stance A/B, 2026-09-26)."""
from __future__ import annotations

from drive_controller import DriveController, SIM_WALK_START_HIP_DEG, SIM_WALK_START_KNEE_DEG


def test_plant_reports_default_and_overrides():
    d = DriveController(dry_run=True)
    assert d.handle("PLANT") == f"PLANT {SIM_WALK_START_HIP_DEG:.1f} {SIM_WALK_START_KNEE_DEG:.1f}"
    assert d.handle("PLANT 20 100") == "PLANT 20.0 100.0"
    assert d.scripted_plant() == (20.0, 100.0)
    assert (d.gait.plant_hip_deg, d.gait.plant_knee_deg) == (20.0, 100.0)
    assert d.handle("PLANT DEFAULT") == f"PLANT {SIM_WALK_START_HIP_DEG:.1f} {SIM_WALK_START_KNEE_DEG:.1f}"
    assert (d.gait.plant_hip_deg, d.gait.plant_knee_deg) == (SIM_WALK_START_HIP_DEG, SIM_WALK_START_KNEE_DEG)


def test_plant_rejects_bad_values():
    d = DriveController(dry_run=True)
    assert d.handle("PLANT 20").startswith("bad PLANT")
    assert d.handle("PLANT 20 200").startswith("bad PLANT")
    assert d.handle("PLANT x y").startswith("bad PLANT")
    assert d.scripted_plant() == (SIM_WALK_START_HIP_DEG, SIM_WALK_START_KNEE_DEG)


def test_plant_refused_while_walking():
    d = DriveController(dry_run=True)
    d._vx = 0.03
    assert d.handle("PLANT 20 100").startswith("PLANT refused")
    d._vx = 0.0
    assert d.handle("PLANT 20 100") == "PLANT 20.0 100.0"
