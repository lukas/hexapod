# cw-walkscratch-easy0905-headset-halfgrav-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-05T12:13:45+00:00

**pod**: hexapod-mjx-train-10

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-c2

**wandb_id**: dd62ifib

**hypothesis**: Plain English: n=3 seed check for the halfgrav-family heading canary (headset-halfgrav-c2, from halfgrav-s2, already reads clean: monotonic reward quarters 25.9/53.5/64.0/98.8). Does a SECOND 0.5g champion (halfgrav-s1) also keep walking under the small discrete heading set {0,+45,-45} on the same unchanged freeprog reward? Same bank-proven recipe/boundaries as the base-family sibling canaries launched this cycle. Cheap 2M canary using idle GPU capacity.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (identical bar to headset-halfgrav-c2): finite losses, real motion, motor-contract compliance, evidence the heading-tracking gradient is live. FAIL only on flat reward/v_along or an immediate park recapture.

**verdict**: CANARY PASS — clean mechanism-health canary, best of the heading-canary cohort so far. 2M steps, reward quarters 25.1/33.6/77.1/100.9 (monotonic, no plateau). Gate harness: 24/24 episodes gait_valid=True, ZERO sacrificed legs anywhere (det/sto/startjitter all clean), 0 falls in 24 episodes, slip/m 1.8-3.0 (median 2.1-2.4, inside the 2.9 teacher band), forward distance 3.2-4.0m/20s episode across all three heading commands (0/+45/-45deg). Duty cycle balanced across all six legs (0.14-0.35, no leg near zero) with high, uniform swing counts -- fast small-stride (2-3cm) cycling but genuinely six-leg, not a parked-leg exploit. Frame strip confirms visibly different robot orientation across the three headings with legs mid-swing, consistent with a live heading-tracking gradient. Clears every clause of the MECHANISM-HEALTH CANARY gate (finite losses, real motion, motor-contract compliance, heading gradient live, no park recapture) with margin to spare. Confirms n=3 for the headset-halfgrav heading-canary family (c2/s1/s3 all pass). Next: fund the 40M acquisition continuation from this seed's own checkpoint (headset-halfgrav-s1acq), matching the c2->acq1 pattern already running.

