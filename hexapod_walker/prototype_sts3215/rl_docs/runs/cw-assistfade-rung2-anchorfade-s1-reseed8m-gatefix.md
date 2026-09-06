# cw-assistfade-rung2-anchorfade-s1-reseed8m-gatefix

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T13:29:12+00:00

**pod**: hexapod-mjx-train-7

**steps**: 8000000

**parent**: cw-assistfade-rung2-anchorfade-s1-reseed8m

**wandb_id**: 11imredg

**hypothesis**: Twin of -s0-reseed8m-gatefix (same one-cycle batch). The anneal gate never latched because the ignition-gate assay had a confirmed code bug (train_ppo_mjx._BcAnchorAnnealGateCb._build() never isolated the assay's goal generator to pure-walk -- root-caused+fixed+tested this cycle, snapshot exp/bc-anchor-anneal-goalmix-fix). This seed's own held-out gate read already clears the 0.35 ignition bar on ALL 4 modes (0.35-0.40) with 0 falls under the still-stuck anchor -- with the assay now measuring correctly, expect the gate to latch within the first 1-2 checks.

**gate**: PASS if (a) bc_anchor_anneal/gate_pass latches within the first ~1-2 checks and coef ramps 3->0, AND (b) the post-anneal held-out det+sto gate eval clears gait_valid, 0 falls, progress_ratio>=0.35 across all 4 modes with the anchor at/near zero. FAIL - MECHANISM if the latch fires but the gait collapses as the anchor fades. FAIL - ASSAY-STILL-BROKEN if the gate still never latches despite the fix -- DIG-IN, do not same-recipe retry again.

