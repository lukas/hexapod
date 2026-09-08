# cw-walkscratch-crutchoff-s1-widen8-swinggap-target150-alone

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T19:44:18+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-crutchoff-s1-widen8-loadslip-target6-cap02-alone

**wandb_id**: fxjvjr3o

**hypothesis**: Plain English: seed1 twin of the s0 swing-gap arm launched this same window -- does the brand-new duration-since-last-swing charge (reward.walk_leg_swing_gap_charge=150, grace_s=3.0, cap_s=4.0) stay mechanism-healthy (no reward collapse) and does it move gait_valid/leg-sacrifice at all, replicating whatever the s0 arm finds? Same isolated recipe/init (duty-ratio-charge=0, loadslip-ratio-charge=0, only the new swing-gap charge live, clean pre-any-charge widen8-acq1 init) so this seed's own result cannot be confounded by either prior per-leg charge.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY (first-ever read of a brand-new mechanism, same budget as every sibling canary in this family): PASS-worth-CONTINUE if (a) reward stays bounded across all 4 training-quarter medians (no order-of-magnitude collapse vs this seed's own widen8-acq1 baseline's typical per-quarter scale) AND (b) 0 new falls vs the widen8-acq1 baseline. FAIL-MECHANISM if reward collapses by orders of magnitude the way the uncapped loadslip charge did before its own cap. Efficacy (>=3/4 of the 4 held-out groups jointly improving slip+progress vs the widen8-acq1 baseline, this family's standing bar) is read and reported but NOT required for a PASS at this first canary depth. Read together with the s0 twin before drawing a family-level conclusion.

