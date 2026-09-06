# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-c1-s2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-06T13:05:11+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-c1

**wandb_id**: s5n23av4

**hypothesis**: Second reproducibility seed (n=3 total with seed2/seed3) for the crutch-ON/kick-fully-off full-realism composite whose seed-2 lineage fell 2/24 at 40M ACQ despite a clean 2M canary -- per the operator's own seed pass-rate batching guidance (08-22), launch the whole small grid in one cycle rather than one arm per decision cycle. Same recipe/init-from checkpoint as -s1, only the seed differs.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same as -s1: CANARY PASS/HOLDS if gait_valid stays majority (>=18/24) with 0 falls at 2M. Read all 3 seeds (2/3/4) together once canaries land: 3/3 clean canaries + any later ACQ fall pattern would indicate a systemic per-seed-lottery fragility in this exact composite recipe, not a one-off.

**verdict**: CANARY FAIL - MECHANISM: fails its own pre-registered bar on BOTH clauses. Evidence: 2M mechanism-health canary, held-out gate 24 eps: gait_valid only 15/24 (below the 18/24 majority bar), 3 tilt_roll terminations (walk/det, walk/sto, walk_startjitter/sto -- one per mode), sacrificed legs now CONCENTRATED on the rear pair (leg4 x4 episodes, leg5 x4 episodes, leg1 x1) rather than scattered -- a chronic weak-leg-pair signature, worse than s1's scattered pattern. Why: 3rd independent seed on the SAME full ~30-axis kick-off composite whose seed-0 2M canary read a clean 0-falls/19-24gv PASS. What's next: combined with s1's own FAIL this cycle, 2/3 seeds now fail the identical 2M mechanism-health canary that item(1)'s original 'kick was the sole broken ingredient' finding was based on (s0 only) -- this settles the doc's own seed-lottery-vs-recipe-fragility fork as RECIPE-FRAGILE, not seed noise. DIG-IN flagged (not verdicted here) on the acq1 (s0, 40M) companion run for the combined cross-seed writeup + next isolation step (which of the ~29 remaining non-kick axes interacts with seed init to produce tilt_roll, concentrating on legs 4/5).

