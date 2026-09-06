# cw-walkscratch-easy0905-headset-crossgrav-medhead-irrwiden-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ_PASS

**created**: 2026-09-06T06:13:03+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-irrwiden-c1

**wandb_id**: mdxo6qac

**hypothesis**: The irr-then-widen composite (irr-timing jitter + 8-way heading, composed on medhead) holds at full 40M ACQ scale, matching its own 2M canary (23/24) and its widen-then-irr sibling's precedent.

**gate**: ACQ PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) with no NEW chronic single-leg pattern; ACQ FAIL - MECHANISM/ENTRENCHES if a leg[1,4]-style or leg-2/5-worsening chronic sacrifice emerges.

**verdict**: The irr-then-widen composite holds its own 2M canary (23/24) at 40M ACQ scale: 22/24 gait_valid, 0 falls. Evidence: the only 2 flagged episodes (walk/det ep3, walk/sto ep5, both leg5) are the SAME episode indices as the 2M canary's own pre-existing leg-2/5 signature (canary duty leg5=0.02 ep3; this run 0.05 ep3, 0.10 ep5 -- flat/marginal, not worsening in magnitude or spreading to new episodes/modes). Matches the sibling widenirr-c1-acq1 (reverse composition order) and the established medhead-irrfwd-c1-acq1 precedent: leg-2/5 softening reproduces rather than entrenches on this recipe. contact_sheet.png video-confirmed genuine six-leg cycling with forward translation, no drag/collapse. W&B reward quarters -317/-274/-58/146 (08-21 rising-reward pattern, consistent with a real late-training gait refinement, not decay). Next: this closes composition-order-irrelevance at ACQ scale for the irr+widen axis pair (both orders now hold at 40M); no further continuation needed on this specific arm.

