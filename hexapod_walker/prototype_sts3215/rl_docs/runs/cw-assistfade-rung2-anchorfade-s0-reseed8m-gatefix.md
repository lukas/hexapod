# cw-assistfade-rung2-anchorfade-s0-reseed8m-gatefix

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ PASS

**created**: 2026-09-06T13:25:53+00:00

**pod**: hexapod-mjx-train-4

**steps**: 8000000

**parent**: cw-assistfade-rung2-anchorfade-s0-reseed8m

**wandb_id**: m1wc03cy

**hypothesis**: The reseed8m pair's anneal gate never latched not because the policy fails to walk cleanly, but because the ignition-gate assay itself had a confirmed code bug (train_ppo_mjx._BcAnchorAnnealGateCb._build() never isolated the assay's goal generator to pure-walk, so most assay episodes silently drew a non-walk goal with no .vx trajectory, poisoning cmd_prog_frac to NaN every round regardless of falls -- root-caused+fixed+tested this cycle, snapshot exp/bc-anchor-anneal-goalmix-fix). Both -reseed8m held-out gate reads already show 0 falls/24 gait_valid with progress_ratio at-or-near the 0.35 ignition bar under the STILL-STRONG anchor (s1: 0.35-0.40 all 4 modes; s0: 0.32-0.44, borderline on 2 modes) -- with the assay now measuring correctly, the anchor should latch+anneal within the first few 500k-step checks and this budget should deliver a genuine post-anneal ignition read.

**gate**: PASS if (a) bc_anchor_anneal/gate_pass latches within the first ~2-3 checks and bc_anchor_anneal/coef visibly ramps 3->0, AND (b) the post-anneal held-out det+sto gate eval clears gait_valid, 0 falls, progress_ratio>=0.35 across all 4 modes with the anchor at/near zero. FAIL - MECHANISM if the latch fires but the gait collapses as the anchor fades. FAIL - ASSAY-STILL-BROKEN if the gate still never latches despite the fix (a second, different assay defect) -- DIG-IN, do not same-recipe retry again.

**verdict**: Result: rung-2 anchor-fade MECHANISM WORKS end-to-end for the first time on real training, both pre-registered clauses met. (a) bc_anchor_anneal/gate_pass latches at global_step ~1.03M (the 2nd in-training check, well inside the 'first 2-3 checks' bar) and train/bc_coef ramps linearly 3.0->0.0 over the next ~4M steps, holding at 0 for the remaining ~3M of the 8M budget -- confirms the 09-06 13:2x goal-mix-isolation fix actually cures the NaN-poisoned assay that blocked both prior -reseed8m attempts. (b) the post-anneal held-out det+sto gate eval (anchor at 0) clears the ignition bar on ALL 4 modes: gait_valid 6/6 in walk/walk_startjitter x det/sto (24/24 total), 0 falls/terminations across all 24 episodes, sac=[] everywhere (no permanently planted/unloaded leg), progress_ratio med 0.41-0.49 (bar 0.35) in every mode. Reward quarters 312.6/1045.8/1271.4/1296.8, still rising/plateauing, no collapse. Video (contact sheets + zoomed frame strips, walk_det_0) shows continuous six-leg cycling and forward translation, matching the gait_valid numbers -- no hidden shuffle. Per the doc's own ignition-gate rule, slip/current are recorded not gated at this stage: slip_per_m runs 2.83-3.82 (mildly above the mature 2.9 joystick band, expected/accepted at ignition, not a fail signal). Why this matters: this is the first random-weight-init rung-2 run to complete the FULL anneal (gate latch -> ramp -> hold-at-zero) end-to-end AND pass the post-anneal held-out ignition bar -- rung 2 (anchor fade from random weights) now has a working, reproducible mechanism, not just a mid-anneal snapshot. Next: verdict the -s1-reseed8m-gatefix twin once its own gate lands (still RUNNING at cycle start, another cycle's to read) for a 2-seed confirmation; if it also passes, rung 2 graduates to hardening (speed band / fixed headings / command changes per the doc's own ladder) and SKILLS.md gets an entry citing both seeds together.

