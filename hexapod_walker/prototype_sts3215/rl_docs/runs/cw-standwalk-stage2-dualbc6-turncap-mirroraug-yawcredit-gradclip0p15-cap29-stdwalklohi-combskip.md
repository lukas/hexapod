# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-combskip

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-03T16:29:42+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklo-hi

**wandb_id**: 36bspx24

**hypothesis**: Plain English: this cycle's zero-training probe found the scripted teacher's OWN turn authority collapses when forward speed is commanded at the same time as a turn (33% of pure-turn wz retained combined); the walk BC-anchor imitates that degraded reference on every combined tick, so removing anchor supervision only on combined ticks (new train.bc_anchor_walk_combined_skip=1.0, mirror of the already-refuted pure-turn-only bc_anchor_walk_turn_skip, green in test_bc_anchor.py) might let the course/yaw reward alone recover more combined-tick turn authority on top of the current-best cap29-stdwalklo-hi recipe, without hurting straight-walk or pure-turn ticks (untouched by this gate by construction).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. 2M-step canary vs the already-run matched control (cap29-stdwalklo-hi, identical recipe minus this flag): PASS if probe_turn_authority.py --vx-cmds combined-tick wz_med (vx=0.08,wz=+-0.25) on this checkpoint beats the checkpoint-scope combined read from this cycle's probe (yawdensity_canary_s1: +0.145/-0.107, i.e. 74%/54% of pure-turn retained) without a pure-turn or straight-walk regression >10% vs control, and without new terminations on a walk-only flat DR-0 proxy read; FAIL if combined wz_med is flat/worse or course/direction_err_med/gait_valid regress vs control.

