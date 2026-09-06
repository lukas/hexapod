# cw-assistfade-rung2-anchorfade-s0-reseed8m-gatefix

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T13:24:05+00:00

**pod**: hexapod-mjx-train-4

**steps**: 8000000

**parent**: cw-assistfade-rung2-anchorfade-s0-reseed8m

**hypothesis**: The reseed8m pair's anneal gate never latched not because the policy fails to walk cleanly, but because the ignition-gate assay itself had a confirmed code bug (train_ppo_mjx._BcAnchorAnnealGateCb._build() never isolated the assay's goal generator to pure-walk, so ~50-60% of assay episodes silently drew a non-walk goal with no .vx trajectory, poisoning cmd_prog_frac to NaN every round regardless of falls -- root-caused+fixed+tested this cycle, snapshot exp/bc-anchor-anneal-goalmix-fix). Both -reseed8m held-out gate reads already show 0 falls/24 gait_valid with progress_ratio at-or-above the 0.35 ignition bar under the STILL-STRONG anchor (s1: 0.35-0.40 all 4 modes; s0: 0.32-0.44, borderline on 2 modes) -- with the assay now measuring correctly, the anchor should latch+anneal within the first few 500k-step checks and this budget should deliver a genuine post-anneal ignition read.

**gate**: PASS if (a) bc_anchor_anneal/gate_pass latches within the first ~2-3 checks (matching the held-out read's already-passing progress) and bc_anchor_anneal/coef visibly ramps 3->0, AND (b) the post-anneal held-out det+sto gate eval clears gait_valid, 0 falls, progress_ratio>=0.35 across all 4 modes with the anchor at/near zero. FAIL - MECHANISM if the latch fires but the gait collapses as the anchor fades. FAIL - ASSAY-STILL-BROKEN if the gate still never latches despite the fix (would mean a second, different assay defect) -- DIG-IN, do not same-recipe retry again.

**refused_reason**: config twin of RUNNING cw-assistfade-rung2-anchorfade-s0-reseed8m (identical train args+steps; a seed twin would differ in --seed — pass --allow-twin only for a deliberate replica)

