# cw-walkscratch-easy0905-headset-crossgrav-medhead-widenirr-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ_PASS

**created**: 2026-09-06T05:52:04+00:00

**pod**: hexapod-mjx-train-8

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-widenirr-c1

**wandb_id**: eipegd5n

**hypothesis**: The widen-then-irr composite (8-way heading + irr-timing jitter, composed on medhead) holds at full 40M ACQ scale, matching its own 2M canary (22/24) and its irr-then-widen sibling's precedent.

**gate**: ACQ PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) with no NEW chronic single-leg pattern; ACQ FAIL - MECHANISM/ENTRENCHES if a leg[1,4]-style or leg-2/5-worsening chronic sacrifice emerges.

**verdict**: The widen-then-irr composite (reverse order of irrwiden) holds its own 2M canary at 40M ACQ scale: 22/24 gait_valid, 0 falls. Evidence: the 2 flagged episodes (walk/det ep3, walk/sto ep5, both leg5) are EXACTLY the same episode indices AND same sac list as the 2M canary -- not a single new flag, not a spread to any other mode/episode across all 24. This is the flattest possible confirmation of the campaign's leg-2/5-reproduces-not-worsens finding. contact_sheet.png video-confirmed genuine six-leg cycling with forward translation, no drag/collapse. W&B reward quarters -90/65/247/512 (08-21 rising-reward pattern). Next: with BOTH composition orders (irrwiden and widenirr) now confirmed ACQ-durable and flat vs canary, composition-order-irrelevance for the irr+widen axis pair is closed at ACQ scale; no further continuation needed on this specific arm.

