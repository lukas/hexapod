# cw-walkscratch-easy0905-headset-halfgrav-s3acq

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T13:23:09+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-s3

**wandb_id**: uwewt762

**hypothesis**: Plain English: the heading canary (headset-halfgrav-s3) clears the mechanism-health bar (0/24 det falls, slip in-band) but shows a leg-1 partial-drop in det mode -- this gives it the full 40M acquisition budget to see whether more budget resolves the leg-1 drop (as clean six-leg cycling matures) or hardens it into a real sacrificed-leg exploit, matching sibling to headset-halfgrav-acq1/s1acq. Warm-started from headset-halfgrav-s3's own 2M checkpoint (own-track, not a teacher/BC/motion-prior).

**gate**: Acquisition milestone at OWN physics (0.5g) + heading: 20s held-out episodes across the 3-heading set, >=0.03 m/s median net forward along each commanded heading, 0 falls in 12 det episodes, SIX-LEG lift/place on video with no persistently sacrificed leg (watch leg 1 specifically), no belly drag; report sto. Per 08-21 ruling: continue/realign if still climbing at cutoff rather than an auto-fail; if leg 1 hardens into a permanent sacrifice at full budget, name and bank the exploit rather than passing on scalars alone.

**refused_reason**: hexapod-mjx-train-1 already runs cw-walkscratch-easy0905-headset-halfgrav-s3acq — GPU pods host exactly one run; pick a free GPU pod.

**note**: ledger self-repair: launch_run.py raced its own just-started trainer process and mis-REFUSED the launch it had itself already kexec'd (pid confirmed alive via ps + wandb run uwewt762 genuinely RUNNING on train-1 at launch time) -- corrected by hand since the mechanical launcher missed it; no duplicate process involved.

