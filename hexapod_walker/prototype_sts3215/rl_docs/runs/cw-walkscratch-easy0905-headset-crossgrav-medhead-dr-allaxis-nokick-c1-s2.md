# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-c1-s2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T13:05:11+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-c1

**wandb_id**: s5n23av4

**hypothesis**: Second reproducibility seed (n=3 total with seed2/seed3) for the crutch-ON/kick-fully-off full-realism composite whose seed-2 lineage fell 2/24 at 40M ACQ despite a clean 2M canary -- per the operator's own seed pass-rate batching guidance (08-22), launch the whole small grid in one cycle rather than one arm per decision cycle. Same recipe/init-from checkpoint as -s1, only the seed differs.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same as -s1: CANARY PASS/HOLDS if gait_valid stays majority (>=18/24) with 0 falls at 2M. Read all 3 seeds (2/3/4) together once canaries land: 3/3 clean canaries + any later ACQ fall pattern would indicate a systemic per-seed-lottery fragility in this exact composite recipe, not a one-off.

