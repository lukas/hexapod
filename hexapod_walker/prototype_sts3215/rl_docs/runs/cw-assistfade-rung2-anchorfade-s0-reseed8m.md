# cw-assistfade-rung2-anchorfade-s0-reseed8m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T12:06:23+00:00

**pod**: hexapod-mjx-train-4

**steps**: 8000000

**parent**: cw-assistfade-rung2-anchorfade-s0

**wandb_id**: jekexee3

**hypothesis**: The anchor-fade mechanism was deadlocked only by its own pinned assay, not by the policy: with a fresh assay seed each round (train.bc_anchor_anneal_assay_reseed=1, built after the cont8m root-cause) the 2M parent checkpoint -- which already passes the held-out ignition bar (det prog 0.36-0.52, 24/24 gait_valid, 0 falls) -- should latch the ignition gate within a few 500k-step rounds, anneal bc_coef 3->0 over 4M steps, and keep walking without the anchor. Same config/budget as cont8m otherwise; inits from the parent 2M checkpoint, NOT the degraded cont8m end (det prog fell to 0.30 under the stuck anchor).

**gate**: PASS if (a) bc_anchor_anneal/gate_pass latches and bc_anchor_anneal/coef visibly ramps 3->0 in wandb_history, AND (b) the post-anneal held-out det+sto gate eval still clears the ignition bar (gait_valid, 0 falls, progress_ratio>=0.35 across all 4 modes) with the anchor at/near zero. FAIL - MECHANISM if the latch fires but the gait collapses (falls/sacrificed leg) as the anchor fades, or the anchor loss diverges/NaNs. FAIL - ASSAY-DISTRIBUTION if reseeded rounds STILL never latch across >=8 rounds with early_term persistently >0: that would mean a genuine double-digit fall rate on the training distribution, contradicting the held-out 0/24 read, and the assay-vs-panel distribution gap becomes the next question. Canary walk_fwd auto-stop stays armed; a stop DURING the fade with reward rising is read per the 08-21 ruling against the coef value at stop time, not as a reflex FAIL.

