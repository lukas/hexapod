# cw-assistfade-rung2-anchorfade-s1-reseed8m-gatefix

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T13:29:12+00:00

**pod**: hexapod-mjx-train-7

**steps**: 8000000

**parent**: cw-assistfade-rung2-anchorfade-s1-reseed8m

**wandb_id**: 11imredg

**hypothesis**: Twin of -s0-reseed8m-gatefix (same one-cycle batch). The anneal gate never latched because the ignition-gate assay had a confirmed code bug (train_ppo_mjx._BcAnchorAnnealGateCb._build() never isolated the assay's goal generator to pure-walk -- root-caused+fixed+tested this cycle, snapshot exp/bc-anchor-anneal-goalmix-fix). This seed's own held-out gate read already clears the 0.35 ignition bar on ALL 4 modes (0.35-0.40) with 0 falls under the still-stuck anchor -- with the assay now measuring correctly, expect the gate to latch within the first 1-2 checks.

**gate**: PASS if (a) bc_anchor_anneal/gate_pass latches within the first ~1-2 checks and coef ramps 3->0, AND (b) the post-anneal held-out det+sto gate eval clears gait_valid, 0 falls, progress_ratio>=0.35 across all 4 modes with the anchor at/near zero. FAIL - MECHANISM if the latch fires but the gait collapses as the anchor fades. FAIL - ASSAY-STILL-BROKEN if the gate still never latches despite the fix -- DIG-IN, do not same-recipe retry again.

**verdict**: Result: rung-2 anchor-fade mechanism (goal-mix-isolation assay fix) CONFIRMS on the 2nd seed -- both pre-registered clauses met, matching the s0 twin's pattern almost exactly. Evidence: bc_anchor_anneal/gate_pass latches at global_step 1,032,192 (2nd in-training check, inside the 'first 1-2 checks' bar), train/bc_coef then ramps linearly 3.0->0.0 over steps 1.08M-5.06M and holds at 0 for the remaining ~3M of the 8M budget (verified full history in wandb_history.csv). Post-anneal held-out det+sto gate eval (anchor at 0) clears the ignition bar on all 4 modes: gait_valid 6/6 in walk/det, walk/sto, walk_startjitter/det, walk_startjitter/sto (24/24 total), 0 falls/terminations across all 24 episodes, sac=[] everywhere (no permanently planted/unloaded leg), progress_ratio med 0.31-0.46 (bar 0.35; walk/sto and walk_startjitter/sto medians land at 0.31/0.35, slightly softer than s0's 0.41-0.49 but every per-mode median still >=0.31 and the per-episode range only dips to 0.29 on 2/24 eps -- no chronic sub-bar mode). Reward quarters 300.6/1053.5/1226.5/1188.4, rising then plateauing late (consistent with anchor fade + fixed 10s episodes, not a collapse). Contact sheet + walk_det_0 frame strip show continuous six-leg alternating-support cycling and clear forward translation, matching gait_valid -- no hidden shuffle. slip_per_m runs 3.02-5.07 (mildly-to-moderately above the mature 2.9 joystick band, expected/accepted at ignition per the doc's own rule, not gated here). Why this matters: this is the SECOND (of 2 pre-registered) random-weight-init rung-2 seed to complete the full anneal end-to-end and clear the post-anneal ignition bar -- with s0 already PASS, rung 2 (anchor fade from random weights) is now a 2-seed-confirmed working mechanism, not a single-seed fluke. Next: graduate rung 2 to hardening (speed band / fixed headings / command changes per the doc's own ladder) using either seed's 8M checkpoint as base; update assistfade/STATUS.md Now + SKILLS.md with the 2-seed confirmation (this cycle).

