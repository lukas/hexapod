Update, 2026-09-03 ~10:3x: **item 1 (resamplematch/turndiet-canary-s1)
CANARY PASS (mechanism)/behavioral: diet-match REFUTED as the sole
steering-gap driver, cross-seed replicated.** `turndiet-canary-s1`
(seed 1 of the resamplematch pair): `probe_turn_authority` is strong
(wz_med 0.216-0.220/-0.177-0.180 rad/s vs +-0.25 cmd, err_med
0.064-0.074, well above the 0.07 floor) — turn AUTHORITY is intact.
But a same-instrument fast walk-only read (`eval_checkpoint.py
--modes walk`, n=16 x {dr0,ownDR} x {det,sto} = 64 eps, no video,
spare pods) shows the diet-match lever does NOT cleanly win:
`direction_err_med` 37.6/42.5/39.8/44.1deg is flat-to-worse vs the
44.56/43.6deg session baseline (no subgroup clears >=20%);
`course_err_1s_med` is a genuine mixed bag — 30-45% BETTER under
DR-0 (15.1/18.3 vs 22.6-28.2 baseline) but 65-100% WORSE under own-DR
det (44.8 vs 22.6-28.2); `slip_per_m_med` is UNIFORMLY WORSE in every
subgroup (3.47/4.54/4.50/4.65) vs both the session baseline
(2.82-2.94) and a newly-established same-instrument PARENT baseline
(`stdwalklohi-acq1` own fastwalkcheck: 2.29/2.92/2.97/3.12,
`logs/ckpt_eval/standwalk_stdwalklohi_acq1_s0_fastwalkcheck/`) —
breaching the gate's ~3.0 slip ceiling every time. Termination rate
(1/16 owndr/sto) matched the PARENT's own established own-DR noise
floor (also 1/16 in that subgroup), not a new fall mode. Video frame
strips confirm clean six-leg gait, gait_valid 1.0 throughout.
**Cross-seed replicated** almost number-for-number by the
`resamplematch-canary` sibling (seed 0, verdicted separately, harsher
CANARY-FAIL: a NEW immediate-tilt own-DR fall, 3/16 owndr/det eps —
**this cycle's own raw fastcheck data for that SAME checkpoint shows
0/16 terms in that subgroup**, a discrepancy between two nominally-
identical `eval_checkpoint.py` reads worth a future dig-in, not
reconciled here; direction/course/slip numbers agree closely either
way). Net conclusion both readings share: the diet mismatch is NOT
the (sole) driver — matching it buys DR-0-only, inconsistent course
gains at a real slip/own-DR cost. (Addendum: the resamplematch-canary
verdict's falls sub-claim was REVISED after this cross-check — my
own-DR 3/16-terms read reproduced byte-identical across 2 of my own
invocations, but is unreconciled against this cycle's 0/16-terms read
of the same checkpoint; likely a knife-edge own-DR draw landing on
opposite sides of the tilt_roll boundary between processes, not a
clean deterministic difference. Dig-in flagged in
OPERATOR_QUESTIONS.md, doesn't change the FAIL verdict — steering-
not-improved + slip-breach alone already fails the gate's PASS bar.)
**Both mild-dose canary seeds now RUNNING**
(`cap29-stdwalklohi-resamplematch-mild-canary` train-1,
`-mild-canary-s1` train-2, seed pair launched this cycle, ~2M steps
each, near done at cycle end) — read both before any further
diet-family arm. If they also fail, pivot
to structural turn-authority (not diet): probe-confirmed authority is
strong turn-IN-PLACE; untested is whether forward+turn CO-OCCURRENCE
is under-trained (`walk_yaw_zero_frac=0.5`/`walk_turn_in_place_
frac=0.30` held constant across every diet arm so far).
