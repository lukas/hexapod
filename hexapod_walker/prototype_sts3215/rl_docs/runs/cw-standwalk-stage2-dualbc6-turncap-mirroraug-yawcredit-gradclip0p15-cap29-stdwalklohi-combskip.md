# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-combskip

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-03T16:29:42+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklo-hi

**wandb_id**: 36bspx24

**hypothesis**: Plain English: this cycle's zero-training probe found the scripted teacher's OWN turn authority collapses when forward speed is commanded at the same time as a turn (33% of pure-turn wz retained combined); the walk BC-anchor imitates that degraded reference on every combined tick, so removing anchor supervision only on combined ticks (new train.bc_anchor_walk_combined_skip=1.0, mirror of the already-refuted pure-turn-only bc_anchor_walk_turn_skip, green in test_bc_anchor.py) might let the course/yaw reward alone recover more combined-tick turn authority on top of the current-best cap29-stdwalklo-hi recipe, without hurting straight-walk or pure-turn ticks (untouched by this gate by construction).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. 2M-step canary vs the already-run matched control (cap29-stdwalklo-hi, identical recipe minus this flag): PASS if probe_turn_authority.py --vx-cmds combined-tick wz_med (vx=0.08,wz=+-0.25) on this checkpoint beats the checkpoint-scope combined read from this cycle's probe (yawdensity_canary_s1: +0.145/-0.107, i.e. 74%/54% of pure-turn retained) without a pure-turn or straight-walk regression >10% vs control, and without new terminations on a walk-only flat DR-0 proxy read; FAIL if combined wz_med is flat/worse or course/direction_err_med/gait_valid regress vs control.

**verdict**: CANARY FAIL - MECHANISM (seed0). Ran probe_turn_authority.py --vx-cmds on this checkpoint (goal.walk_yaw_cmd=1, mesh/100Hz cfg, wz=+-0.25 x vx=0/0.08, probe-seeds 0/1) plus the matched control cap29-stdwalklo-hi under the identical probe. Pure-turn wz_med: this ckpt +0.195/-0.191 vs control +0.223/-0.250 -> regression 12.7% (+) / 23.7% (-), both over the pre-registered 10% cap. Combined-tick (vx=0.08) wz_med: this ckpt +0.116/-0.145 vs the pre-registered comparator (yawdensity_canary_s1) +0.145/-0.107 -> negative side beats it (+35% magnitude) but positive side is WORSE, so it does not clear 'beats comparator both signs'. Per the pre-registered gate (PASS needs both: beat comparator combined AND <=10% pure-turn regression vs control), this fails on the regression clause alone, reproduced on the seed1 twin (see its own verdict). Why: bc_anchor_walk_combined_skip removes BC supervision on combined ticks hoping the course/yaw reward alone recovers authority; it traded pure-turn accuracy for a partial, sign-asymmetric combined-tick gain, not a clean win. Next: branch (a) (tripod_gait.py combined vx+omega foot-target geometry fix) is now the sole remaining candidate per standwalk STATUS Next item 2; do not retry combined-tick BC-skip alone. Evidence: logs/ckpt_eval/probe_turn_authority_combskip_s0_combined_09-03.json, probe_turn_authority_cap29_stdwalklo_hi_combined_09-03.json.

