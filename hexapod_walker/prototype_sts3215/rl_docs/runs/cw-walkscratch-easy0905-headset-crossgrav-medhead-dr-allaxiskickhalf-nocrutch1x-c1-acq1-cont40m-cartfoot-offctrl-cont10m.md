# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-cartfoot-offctrl-cont10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T05:56:59+00:00

**pod**: hexapod-mjx-train-0

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-cartfoot-offctrl

**wandb_id**: x46hb1dy

**hypothesis**: Plain English: matched control for cartfoot-c1-cont10m -- the same +10M continuation with the ORIGINAL joint decode (no cart keys), giving the joint-parameterization's gait/slip/progress band at the identical 12M cumulative depth and RNG2 so the Cartesian arm's convergence read is causal, not a depth artifact.

**gate**: 24-ep gate: PASS = retention of the source band (0 falls, gait_valid 21-24/24, slip ~5-6/m det band, no new chronic single-leg sacrifice) -- then it IS the comparison band for cartfoot-c1-cont10m; if this control itself drifts, read the continuation pair as inconclusive rather than crediting/blaming the mechanism.

