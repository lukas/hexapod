# standwalk STATUS journal archive — 2026-09-02h (verbatim trim)

Trimmed from the top of `rl_docs/tracks/standwalk/STATUS.md` on
2026-09-02 ~23:5x to keep the live file under its 120-line budget.
These entries are historical; do not act on them, read the live
STATUS.md's current top entry instead.

Update, 2026-09-02 ~23:1x (idle-kick, item 0's read still mid-flight):
**ROOT-CAUSED + FIXED the `k_walk_course_income` regression the ~22:2x
entry below flagged for a dedicated dig-in.** Not the reward mechanism
-- a stale plant-stance literal. The b7e7ea05 merge switched
`sim_env.py`'s internal TripodGait use from the `sim_gait_compat`
wrapper (mujoco-relative knees) to the raw absolute-tibia gait (the
whole env now speaks `robot_abs` at the physics boundary, a real and
mostly-correct refactor) but left `_default_plant_deg()`'s stance
literal and `_make_walk_bc_gait`'s `sync_plant_stance(20.0, 80.0)`
un-converted: 80 was always the MUJOCO-RELATIVE knee value; relabeling
it as robot_abs without converting makes the physical knee 20 deg
LESS bent (`mujoco_rel = robot_abs_knee - hip = 80-20=60`, not the
intended 80). Measured (static-hold "park" episode, 8s): chassis rode
+82mm above the reset-settled height, `reward_height` -436,
`reward_loadslip_excess` -160, total park reward -1168 (historical
~+90). Fix: literal 80 -> **100** (its robot_abs equivalent, 80+hip 20)
in both call sites -- post-fix the same probe holds height_err_mm
~13mm all episode, loadslip/drag -> 0, total park reward **+89**,
matching history. Bank effect: `test_course_income_semantics.py`
7fail/5pass -> 4fail/8pass; `test_course_disp_semantics.py` +
`_window` -> 1fail/37pass (a margin edge, not a mechanism break);
`test_phasedir_semantics.py` + `test_quad_body_frame_trim.py`
(disposable-worktree pre/post cross-check) 17fail/19pass ->
10fail/26pass, ZERO new failures anywhere (the one remaining
quad_body_frame_trim failure is identical pre- and post-fix,
pre-existing, unrelated). Full derivation + numbers:
`OPERATOR_QUESTIONS.md` 2026-09-02 ~23:1x entry. Remaining follow-up
for whoever next touches this: retune the 4 still-failing
course_income margin constants against the now-correct physics (they
read as genuine recalibration, not further bugs -- the module's own
docstring already flags `backward`-vs-`park` as a historically tight
tradeoff), and triage the 10 still-failing phasedir cases (untouched
this cycle, different reward stack). Two full-bank pytest runs
(the ~22:2x entry's 398-test regression, PID 186875 from 22:19; this
entry's own `test_task_semantics`+`joint_action_{bias,box}` recheck
from 22:55) are BOTH still running past this cycle's exit -- read
them first. Snapshotted+pushed. This is CODE work (a real sim-physics
bug affecting every walk-mode reward term that reads chassis height/
drag/slip while near the plant stance, i.e. every live standwalk arm)
rather than a training result, so item 0 below (the in-flight
stdwalklohi-acq1 session read) is UNCHANGED/still the track's primary
open item; this fix does not itself require re-running that read.

Update, 2026-09-02 ~22:2x: idle-kick (item 0's read still mid-flight
on train-6/7) found a shared-repo infra emergency mid-cycle and fixed
it before anything else: a concurrent cycle's routine `snapshot.sh`
pull fast-forwarded main onto the operator's `66c4af30` merge, which
DELETED `test_task_semantics.py` + 7 sibling spec files, several
motion-library assets, a BC checkpoint, AND a real `joint_task.py`
mechanism (`goal.joint_action_bias/box_*`) with no replacement code —
collateral damage from an otherwise-legitimate joint-frame-v2 /
"remove pre-v2 compat" cleanup upstream. Restored everything verbatim
from `631d7f4c` (commit `07d0a475`) + fixed one downstream break
(`sim_gait_compat.py`'s `joint_frame` import got renamed out from
under it) + landed the previously-flagged `trans_drag_mm`/
`k_drag_loaded` dt-scaled deadband fix (bit-exact at legacy
`control.hz=25`, correctly tightens at the 100Hz default — the
`test_trans_drag_*` bank now passes 4/4). Full writeup, including one
STILL-OPEN unrelated regression this same merge introduced in
`k_walk_course_income` walk-mode physics (confirmed via a disposable
`631d7f4c` worktree, confirmed NOT caused by the drag fix, not yet
root-caused — flagged for a dedicated dig-in), in
`OPERATOR_QUESTIONS.md` 2026-09-02 ~22:0x entry. Full-bank regression
re-run in flight at cycle end (not read this cycle). Snapshotted+
pushed. Prior 09-02 ~21:3x update (the semantics-bank dig-in that
found this bug) moved verbatim to
`archive/standwalk_STATUS_journal_2026-09-02g_trim.md`.
