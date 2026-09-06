# cw-assistfade-rung2-anchorfade-s1-reseed8m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T12:07:40+00:00

**pod**: hexapod-mjx-train-7

**steps**: 8000000

**parent**: cw-assistfade-rung2-anchorfade-s1

**wandb_id**: qsqewbb5

**hypothesis**: Twin seed of -s0-reseed8m (same one-cycle batch; seed pass-rate n=2). The anchor-fade mechanism was deadlocked only by its own pinned assay: s1-cont8m showed the identical signature (15/15 assay rounds fail at early_term_rate 0.125, coef stuck 3.0, canary walk_fwd 0/2 from 5M). With fresh assay seeds per round the 2M parent checkpoint (held-out ignition bar pass: prog 0.35-0.51, 24/24 gv, 0 falls) should latch, anneal bc_coef 3->0 over 4M, and keep walking without the anchor. Inits from the parent 2M checkpoint, not the degraded cont8m end.

**gate**: PASS if (a) bc_anchor_anneal/gate_pass latches and bc_anchor_anneal/coef visibly ramps 3->0 in wandb_history, AND (b) the post-anneal held-out det+sto gate eval still clears the ignition bar (gait_valid, 0 falls, progress_ratio>=0.35 across all 4 modes) with the anchor at/near zero. FAIL - MECHANISM if the latch fires but the gait collapses (falls/sacrificed leg) as the anchor fades, or the anchor loss diverges/NaNs. FAIL - ASSAY-DISTRIBUTION if reseeded rounds STILL never latch across >=8 rounds with early_term persistently >0 (genuine high fall rate on the training distribution, contradicting the held-out 0/24 read). Canary walk_fwd auto-stop stays armed; a stop DURING the fade with reward rising is read per the 08-21 ruling against the coef value at stop time.

