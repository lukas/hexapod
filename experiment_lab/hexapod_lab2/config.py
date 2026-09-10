"""All knobs in one place, read once from the environment."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _f(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw else default


def _i(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw else default


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    # Dedicated checkout of origin/main that the runner executes from and the
    # builder pushes to. Never the operator's working tree.
    checkout: Path
    robot_url: str = "http://192.168.4.39:8080"
    vision_url: str = "http://127.0.0.1:8766/api/pose-state"
    # The runner's default frame URL (<state dir>/frame.jpg) does not exist on
    # the pose service; without a fetchable frame nothing ever counts as an
    # advancing frame and admission fails before motion.
    vision_frame_url: str = "http://127.0.0.1:8766/snapshot/1.jpg"
    claude_bin: str = "claude"
    planner_model: str = "claude-opus-5"
    builder_model: str = "claude-opus-5"
    # Budgets. The first three are the operator's rules, verbatim.
    health_budget_s: float = 10.0
    postrun_budget_s: float = 60.0
    planner_budget_s: float = 120.0
    builder_budget_s: float = 1800.0
    run_timeout_s: float = 900.0
    planner_max_usd: float = 2.0
    builder_max_usd: float = 15.0
    daily_spend_cap_usd: float = 40.0
    # Loop stop rules.
    max_consecutive_failed_runs: int = 3
    max_consecutive_unreachable: int = 2
    max_consecutive_empty_plans: int = 2
    idle_sleep_s: float = 30.0
    # Trajectory protocols (every *_belly_rest_* and radial-shear replay, not
    # just stands) need the runner's --force gate. The old lab passed it on
    # every one of those runs and the operator asked for no new pre-run gates,
    # so the loop passes it for whole-body protocols. HEXAPOD_LAB2_ALLOW_FORCE=0
    # turns that off.
    allow_force: bool = True
    goal: str = (
        "Get the hexapod walking smoothly: measured joint compliance and "
        "contact behaviour on every leg, then whole-body stands and gaits "
        "that stay inside the robot's own current/temperature/tilt trips."
    )
    extra_env: dict = field(default_factory=dict)

    @property
    def db_path(self) -> Path:
        return self.data_dir / "lab2.sqlite3"

    @property
    def runs_dir(self) -> Path:
        return self.data_dir / "runs"

    @property
    def pause_file(self) -> Path:
        return self.data_dir / "PAUSE"

    @property
    def prototype_dir(self) -> Path:
        return self.checkout / "hexapod_walker" / "prototype_sts3215"

    @property
    def protocols_dir(self) -> Path:
        return self.prototype_dir / "sysid" / "protocols"

    @property
    def python(self) -> Path:
        return self.checkout / ".venv" / "bin" / "python"


def load_settings() -> Settings:
    home = Path.home()
    data_dir = Path(os.getenv(
        "HEXAPOD_LAB2_DATA_DIR",
        home / "Library" / "Application Support" / "Hexapod Lab" / "v2",
    )).expanduser()
    checkout = Path(os.getenv(
        "HEXAPOD_LAB2_CHECKOUT", data_dir / "checkout"
    )).expanduser()
    return Settings(
        data_dir=data_dir,
        checkout=checkout,
        robot_url=os.getenv("HEXAPOD_LAB2_ROBOT_URL", Settings.robot_url),
        vision_url=os.getenv("HEXAPOD_LAB2_VISION_URL", Settings.vision_url),
        vision_frame_url=os.getenv("HEXAPOD_LAB2_VISION_FRAME_URL", Settings.vision_frame_url),
        claude_bin=os.getenv("HEXAPOD_LAB2_CLAUDE_BIN", Settings.claude_bin),
        planner_model=os.getenv("HEXAPOD_LAB2_PLANNER_MODEL", Settings.planner_model),
        builder_model=os.getenv("HEXAPOD_LAB2_BUILDER_MODEL", Settings.builder_model),
        health_budget_s=_f("HEXAPOD_LAB2_HEALTH_BUDGET_S", Settings.health_budget_s),
        postrun_budget_s=_f("HEXAPOD_LAB2_POSTRUN_BUDGET_S", Settings.postrun_budget_s),
        planner_budget_s=_f("HEXAPOD_LAB2_PLANNER_BUDGET_S", Settings.planner_budget_s),
        builder_budget_s=_f("HEXAPOD_LAB2_BUILDER_BUDGET_S", Settings.builder_budget_s),
        run_timeout_s=_f("HEXAPOD_LAB2_RUN_TIMEOUT_S", Settings.run_timeout_s),
        planner_max_usd=_f("HEXAPOD_LAB2_PLANNER_MAX_USD", Settings.planner_max_usd),
        builder_max_usd=_f("HEXAPOD_LAB2_BUILDER_MAX_USD", Settings.builder_max_usd),
        daily_spend_cap_usd=_f("HEXAPOD_LAB2_DAILY_SPEND_CAP_USD", Settings.daily_spend_cap_usd),
        max_consecutive_failed_runs=_i("HEXAPOD_LAB2_MAX_FAILED_RUNS", Settings.max_consecutive_failed_runs),
        allow_force=os.getenv("HEXAPOD_LAB2_ALLOW_FORCE", "1") != "0",
        goal=os.getenv("HEXAPOD_LAB2_GOAL", Settings.goal),
    )
