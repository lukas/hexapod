# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: HARDENING PASS

**created**: 2026-09-06T12:21:11+00:00

**pod**: hexapod-mjx-train-4

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1

**wandb_id**: v6wmk0lv

**hypothesis**: The full ~30-axis DR composite without the torque crutch (dr.torque_scale=1, true unassisted servo spec) just ACQ PASSED at 40M (22/24 gait_valid, 0 falls, matching/improving its own 21/24 canary). Per this campaign's own endurance-testing convention (every clean ACQ PASS gets a cont40m hold-check before champion consideration), continue +40M (80M cumulative) to confirm it is durable past acquisition budget, not just at it -- closes the remaining half of QUEUE AIM items (3)/(4)'s precondition (the crutch-ON sibling allaxis-nokick-c1-acq1 landed the same cycle with 2 falls and is separately DIG-IN flagged; this continuation is independent of that finding).

**gate**: cont40m gate (80M cumulative): PASS/HOLDS if gait_valid stays majority (>=18/24), 0 falls/terminations, no NEW chronic single-leg pattern beyond the 2 scattered non-chronic flags already seen at 40M. FAIL/ENTRENCHES if gait_valid drops below majority, a chronic single-leg pattern emerges, or any fall appears where the 40M parent had none.

**verdict**: The kick-safe/no-torque-crutch full-realism composite HOLDS at 80M cumulative, matching its own 40M parent almost episode-for-episode. gait_valid 22/24 both before and after (walk/det 6/6, walk/sto 5/6, walk_startjitter/det 5/6, walk_startjitter/sto 6/6): the SAME two episodes carry the only flags both times (walk/sto ep4, walk_startjitter/det ep1), the SAME leg (leg2) is the one flagged in both, and startjitter/det actually narrows from 2 flagged legs ([0,2]) at 40M to 1 ([2]) at 80M -- reproduction/mild improvement, not new entrenchment. 0 falls/terminations anywhere at either budget. Slip stays elevated (median ~5-5.4/m across modes, up to 13/m on the two flagged episodes) which is the expected, non-gated cost of removing the torque crutch, not a regression vs the 40M parent's own similarly elevated slip. Reward rises every quarter (819.2/1485.4/1598.1/1709.3), no plateau. This satisfies the run's own pre-registered cont40m gate text verbatim (majority gait_valid held, 0 new falls, no new chronic single-leg pattern) and is the CLEANEST endurance read of the two QUEUE-AIM-item(4) composite candidates: its crutch-ON sibling (allaxis-nokick-c1-acq1) landed 2 falls/24 against its own 0-falls ACQ bar and sits DIG-IN flagged/unverdicted, while this crutch-OFF/kick-safe composite now has a clean ACQ AND a clean cont40m hold end to end. Recommend this lineage (checkpoint ppo_goal_cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_allaxiskickhalf_nocrutch1x_c1_acq1_cont40m) as the settled champion for QUEUE AIM item(4) (full-realism composite, no crutch) pending the allaxis-nokick dig-in's own resolution; next step per QUEUE AIM is the acquisition-milestone panel + contextual DONE-gate rungs (heading changes, slip pressure) on this checkpoint. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_allaxiskickhalf_nocrutch1x_c1_acq1_cont40m_gate/report.json vs ..._acq1_gate/report.json (per-episode leg/slip diff), W&B v6wmk0lv.

