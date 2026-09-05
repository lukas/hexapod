# cw-walkscratch-easy0905-headset-halfgrav-medhead2-swinggate-fix

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY_FAIL

**created**: 2026-09-05T21:57:55+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-medhead2-acq1-cont40m

**wandb_id**: jkh3xzb5

**hypothesis**: This cycle's own verdict on headset-halfgrav-medhead2-acq1-cont40m found ACQ FAIL specifically on walk_startjitter/det (stuck 2/6 gait_valid through 80M) with borderline-low duty (0.05-0.08) on legs that vary episode-to-episode -- a milder version of the same per-leg-utilization underuse the base(1g) family's swing_gate batch is targeting, just not yet hard-parked. Does reward.walk_swing_gate (bank-proved 4/4 green this cycle, already retrofitting 3 base-family entrenched checkpoints in parallel) also lift the flagged legs' duty above the gait_valid bar on this halfgrav/medhead2 lineage's exact FAILED checkpoint, without breaking its already-clean walk/det (5/6) or introducing falls?

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (2M): repair-signal if walk_startjitter/det's previously-flagged legs majority-clear duty>0.10 (matching this family's own accepted-PASS 0.08-0.09+ range) with 0 new falls and walk/det stays >=4/6 gait_valid (no regression from the 5/6 baseline). FAIL - MECHANISM if the same legs stay <0.10 in a majority of episodes regardless of whether walk_swing_gate_factor shows real decline, or if walk/det regresses below 4/6. Read alongside the base-family n=3 swing_gate batch (s0c1/medhead/irr) before concluding swing_gate's effect on this family.

**verdict**: CANARY FAIL - MECHANISM (engaged, no repair). Gate: retrofit reward.walk_swing_gate onto the FAILED halfgrav+medhead2 checkpoint (headset-halfgrav-medhead2-acq1-cont40m, ACQ FAIL on walk_startjitter/det plateaued at 2/6 through 80M) to see if it lifts the flagged legs' duty above 0.10. Evidence: gait_valid counts are IDENTICAL to the undosed parent across all 4 modes (walk/det 5/6, walk/sto 6/6, walk_startjitter/det 2/6, walk_startjitter/sto 4/6) despite only 2M extra steps on top -- every failing episode's flagged-leg duty stays 0.03-0.09, all below the 0.10 pass bar, same leg-varies-episode-to-episode pattern as before. env/walk_swing_gate_factor DID show real engagement (0.93-1.0 sampled, not saturated-inert like the base family's fresh/fix arms) so the dose was live, it just didn't move the behavior. Why: this is the mechanism's per-episode-varying/borderline-duty halfgrav case, read alongside this same cycle's base-family batch (s0c1-fresh, s0c1-fix INERT; medhead-fix, irr-fix engaged-no-repair) -- all 5 independently-tested arms across BOTH gravity families now FAIL. walk_swing_gate is CLOSED end-to-end as a per-leg-utilization repair lever on this sim/reward stack (7th mechanism to fail overall, 1st on halfgrav specifically). What's next: no further walk_swing_gate arms on any checkpoint/family; base(1g) family stays structurally closed (4/4 seeds entrench leg favoritism, 7/7 mechanisms fail) -- reallocating this cycle's free capacity to the halfgrav lineage's validated widen-curriculum approach instead (widen2 2/2 seeds CANARY PASS, acq1 continuations already running; this cycle adds two complementary hybrid arms combining widen2's heading breadth with irr's timing-jitter robustness, the two validated halfgrav rungs closest to the actual composite DONE-gate panel).

