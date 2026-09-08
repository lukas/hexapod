# cw-walkscratch-crutchoff-s0-widen8-swinggap-target150-alone

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T19:42:06+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-crutchoff-s0-widen8-loadslip-target6-cap02-alone

**wandb_id**: 9ewjhp2n

**hypothesis**: Plain English: this tests a brand-new, structurally different anti-leg-sacrifice reward mechanism -- instead of pricing a STATE a dragging/planted leg can fake (low duty-ratio recovers by holding longer, high load-slip-ratio recovers by holding stiller), it prices the PATTERN directly: seconds elapsed since a leg's last real qualifying swing, so a leg can only lower the charge by actually swinging. Both prior per-leg charges (duty-ratio, load-slip-with-cap) were mechanism-healthy (no reward collapse) but never cleared the family's 3/4-groups efficacy bar (0-1/4 groups, 2/2 seeds each) -- this is the first-ever exercise of the swing-gap design those closures named as the next open lead (CURRENT_TRUTHS/walkcurr STATUS 2026-09-08 ~19:1x). Same isolated recipe/init as every sibling in this family (duty-ratio-charge=0, loadslip-ratio-charge=0, ONLY reward.walk_leg_swing_gap_charge=150/grace_s=3.0/cap_s=4.0 live, same clean pre-any-charge widen8-acq1 init) so this seed's own result cannot be confounded by either prior charge. Ships pre-capped from inception (cap_s=4.0) per the loadslip lineage's own lesson that an unbounded per-tick excess drives orders-of-magnitude reward collapse.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY (first-ever read of a brand-new mechanism, same budget as every sibling canary in this family): PASS-worth-CONTINUE if (a) reward stays bounded across all 4 training-quarter medians (no order-of-magnitude collapse vs this seed's own widen8-acq1 baseline's typical per-quarter scale) AND (b) 0 new falls vs the widen8-acq1 baseline. FAIL-MECHANISM if reward collapses by orders of magnitude the way the uncapped loadslip charge did before its own cap. Efficacy (>=3/4 of the 4 held-out groups jointly improving slip+progress vs the widen8-acq1 baseline, this family's standing bar) is read and reported but NOT required for a PASS at this first canary depth -- matches how duty-ratio and loadslip were each first read alone (mechanism-only) before any efficacy claim was expected. Read together with the s1 twin before drawing a family-level conclusion.

