# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-cartfoot-offctrl-s3

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS

**created**: 2026-09-08T06:02:34+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m

**wandb_id**: a2o71f5o

**hypothesis**: Plain English: matched zero/off control for cartfoot-c1-s3 -- the byte-identical seed3 +2M continuation of the cont40m champion with NO cart_foot keys, so the ON seed replicate's read is causal (mechanism vs seed noise) rather than 'seed3 training happened to differ.'

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Retention gate: 0 falls/terminations, gait_valid in-or-above the source's 21-24/24 band, slip/m in the established 5-6/m det band. Serves as the comparison baseline for cartfoot-c1-s3; if this control itself regresses, read the seed3 pair as inconclusive.

**verdict**: CANARY PASS (retention gate, matched control): 0 falls/terminations in 24/24 episodes across all 4 groups; gait_valid 6/6-5/6-5/6-6/6 = 22/24, inside the required 21-24/24 source band; slip/m median 4.93/4.95/4.98/5.72, inside the established 5-6/m det band (not regressed). This control confirms clean at 40M continuation depth, so the already-verdicted ON sibling cartfoot-c1-s3 (CANARY PASS, slip/m 20.55/20.57/31.61/27.15, gait_valid 20/24) is now a formally-completed comparison, not the 'not in doubt but unstamped' state its own verdict left it in: cart_foot-space control on this seed is 4.2-6.3x slippier than joint-space at matched gait_valid, closing the PROMISING stamp as NOT PROMISING for seed 3 (mechanism-viable, materially slippier, matches the seed2 pair's fingerprint almost exactly). Contact sheet shows clean six-leg stance/swing cycling, no flag leg, consistent forward travel. Next: no further action needed on this control; the cartfoot mechanism's slip deficit is now cross-seed-confirmed twice (seed2, seed3) against matched controls both times -- fork (b) fresh-init seeds (s7/s11) are the open question, not more seed3-style continuations.

