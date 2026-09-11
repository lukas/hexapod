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
    # The wide camera. The runner's own frames come from the floor-tag camera,
    # which frames whole-body work as legs at the top edge; the loop records
    # this one at 1 Hz for every run and that is what the eyes look at.
    wide_frame_url: str = "http://127.0.0.1:8766/snapshot/0.jpg"
    eyes_model: str = "claude-sonnet-5"
    # The robot sits small in the wide frame; the eyes look at this crop
    # (x, y, w, h as fractions of the frame) scaled up, not the whole frame.
    wide_crop: str = "0.02,0.0,0.6,0.75"
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
    engineer_max_usd: float = 15.0
    engineer_budget_s: float = 1800.0
    # Merge gate for engineer branches: paths must be under fix_scope and not
    # under any fix_forbidden prefix; total changed lines must stay under
    # max_fix_lines. Anything else is left on its branch for a human.
    fix_scope: str = "hexapod_walker/prototype_sts3215/"
    fix_forbidden: tuple = ("experiment_lab/",)
    max_fix_lines: int = 300
    robot_ssh: str = "arduino@192.168.4.39"
    deploy_timeout_s: float = 240.0
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
    # The one exception to "no pre-run checks", asked for by the operator on
    # 2026-09-11 after the loop started a run while a leg was off and they
    # were fixing it: before moving, look at the wide camera once and ask an
    # open question, "can you see the robot and does it look ready to move?"
    # Inside the 10 s health budget. HEXAPOD_LAB2_LOOK=0 turns it off.
    look_before_moving: bool = True
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
    def robot_held(self) -> Path:
        """Present while an engineer job owns the robot. The loop runs nothing
        until it is gone; the engineer may ssh, flash, deploy and move it."""
        return self.data_dir / "ROBOT_HELD"

    @property
    def deploy_flag(self) -> Path:
        """Present when main carries robot-side code the robot does not have yet.
        The loop deploys between runs, never during one."""
        return self.data_dir / "DEPLOY_NEEDED"

    @property
    def cap_file(self) -> Path:
        """Operator override of the daily cap, set with `hexapod-lab2 cap N` or a
        'raise cap' text. Read every time so it applies without a restart."""
        return self.data_dir / "CAP_USD"

    def current_cap(self) -> float:
        try:
            return float(self.cap_file.read_text().strip())
        except (OSError, ValueError):
            return self.daily_spend_cap_usd

    def set_cap(self, usd: float) -> float:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cap_file.write_text(f"{float(usd):.2f}\n")
        return float(usd)

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
        wide_frame_url=os.getenv("HEXAPOD_LAB2_WIDE_FRAME_URL", Settings.wide_frame_url),
        eyes_model=os.getenv("HEXAPOD_LAB2_EYES_MODEL", Settings.eyes_model),
        wide_crop=os.getenv("HEXAPOD_LAB2_WIDE_CROP", Settings.wide_crop),
        engineer_max_usd=_f("HEXAPOD_LAB2_ENGINEER_MAX_USD", Settings.engineer_max_usd),
        engineer_budget_s=_f("HEXAPOD_LAB2_ENGINEER_BUDGET_S", Settings.engineer_budget_s),
        max_fix_lines=_i("HEXAPOD_LAB2_MAX_FIX_LINES", Settings.max_fix_lines),
        robot_ssh=os.getenv("HEXAPOD_LAB2_ROBOT_SSH", Settings.robot_ssh),
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
        look_before_moving=os.getenv("HEXAPOD_LAB2_LOOK", "1") != "0",
        goal=os.getenv("HEXAPOD_LAB2_GOAL", Settings.goal),
    )
