# cw-walkscratch-easy0905-base-cartfoot-freshoffctrl-s10-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-08T07:15:35+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-base-cartfoot-freshoffctrl-s10

**wandb_id**: 2vfmkuv4

**hypothesis**: Plain English: matched joint-space (no Cartesian-foot-target) control for base-cartfoot-fresh-s10-c1b -- same own-checkpoint +38M continuation of the fresh-init OFF canary, seed 10, so the fork(b) n=3 fresh-init seed cohort (s7 pair running, s11 pair running) gets its third seed's matched control at the same 40M budget instead of only an ON arm running alone.

**gate**: PASS-BAND if it reaches gait_valid/no-falls/slip comparable to the established base-family PASS band (base-s0..s4) on the fixed-forward walk panel. Read paired against base-cartfoot-fresh-s10-c1b at the same cumulative depth: this completes the seed-10 half of the n>=3 fresh-init ON/OFF cohort. FAIL if it cannot reach walking at all by 40M despite sibling base-family seeds all reaching it. Per the 08-21 ruling, judge on reward trend + eval together.

**verdict**: Matched OFF control for the fork(b) fresh-init seed10 pair (paired against ON=base-cartfoot-fresh-s10-c1b, already PASS-PARITY). 0/24 falls, gait_valid 12/12 sto, 0/12 det (same family-wide det-only leg[1]/[4] duty-underuse quirk already precedented non-blocking in halfgrav-s0-c1 and mirrored in the ON run), reward rising every quarter (-402.0->797.8->1630.7->1925.9), no plateau. Frame strips (walk_det_0, walk_sto_0) show level body, steady forward translation, alternating leg swing, no drag/flag-leg. Computed exact ON/OFF slip ratio vs the c1b report: walk/det 0.857x, walk/sto 0.983x, walk_startjitter/det 0.911x, walk_startjitter/sto 0.969x -- ON at-or-under OFF in all 4 groups, matching seed7's PARITY shape (0.94-0.99x) and the opposite of fork(a)'s 1.5-6x inflation. This is the 2nd of 3 planned fresh-init seed replicates to land PARITY (seed7, now seed10); seed11's pair is still training.

