# cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: HARDENING PASS

**created**: 2026-09-06T12:13:41+00:00

**pod**: hexapod-mjx-train-5

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c1-acq1

**wandb_id**: aox3y4ss

**hypothesis**: The full 8-way-heading-incl-reversals widen2 champion (halfgrav, seed c1) ACQ PASSed cleanly at 40M (21/24 gait_valid, 0 falls); sibling c2b FAILED at cont40m, c3 is mid-cont40m elsewhere, c1 is the remaining endurance question. (multiple prior attempts this cycle hit a launch-syntax bug then a transient self-repair tar race then a pod collision; explicit free pod picked here.)

**gate**: HARDENING PASS/HOLDS if gait_valid stays majority (>=18/24) at 80M cumulative with no NEW chronic single-leg pattern and 0 falls. HARDENING FAIL/ENTRENCHES if it drops below majority, a new chronic leg appears, or any fall appears.

**verdict**: HARDENING PASS/WATCH: +40M (80M cumulative) on the halfgrav full-8-way-heading widen2 champion (seed c1) holds majority at 20/24 gait_valid (parent 21/24), 0 falls/terminations either side, reward continuing its own U-shaped-but-net-improving trend (parent ended -1515 mean; this budget's quarters -795/-1148.9/-995.1/-749.2, i.e. less negative, consistent with the parent's own dip-then-recover shape, not a new regression). The one real change worth flagging: leg1 (structurally the composite's weakest leg alongside 0/3, per the parent's own triple-candidate) newly crosses the sacrifice threshold in 3 of 24 episodes (walk/det ep4 -- already flagged for legs 0/3 at 40M, now also flags leg1, i.e. same episode gets one more leg; plus two brand-new single-episode crossings, walk/det ep2 leg0 and walk_startjitter/det ep2 leg1) where the parent had zero leg1 flags. Duty for leg1 in these crossings (0.06-0.10) is close to its already-low baseline duty elsewhere (0.09-0.20) rather than a sudden collapse from a healthy level, and no mode has leg1 (or any leg) out in a majority of its episodes -- still scattered, not chronic, but WATCH leg1 on any further continuation of this exact lineage. HARDENING PASS per the run's own pre-registered numeric bar (>=18/24, 0 falls, no majority-of-episodes chronic leg), with this WATCH caveat attached. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_halfgrav_fullhead_widen2_c1_acq1_cont40m_gate/report.json vs ..._acq1_gate/report.json (per-episode duty), W&B aox3y4ss.

