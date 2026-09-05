# cw-walkscratch-easy0905-headset-halfgrav-s3

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-05T12:12:28+00:00

**pod**: hexapod-mjx-train-9

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-c2

**wandb_id**: btkppya1

**hypothesis**: Plain English: n=3 seed check (third 0.5g champion, halfgrav-s3) for the heading canary, same design as headset-halfgrav-s1 (see that run for full rationale) -- reusing idle GPU capacity per the operator's full-fleet-utilization order.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (identical bar to headset-halfgrav-c2): finite losses, real motion, motor-contract compliance, evidence the heading-tracking gradient is live. FAIL only on flat reward/v_along or an immediate park recapture.

**verdict**: CANARY PASS — clears the mechanism-health bar with a caveat. 2M steps, reward quarters 19.3/52.8/78.0/72.5 (rising overall, small dip in the final quarter, not a plateau). Gate harness: 0/24 falls in det (24/24), 1/24 falls in sto+startjitter combined (one tilt_roll termination), slip/m 1.9-2.6 (median 2.1-2.3, comfortably inside the 2.9 teacher band), forward distance 1.6-4.0m/20s episode across headings. CAVEAT: leg 1 is intermittently sacrificed in the det-mode variants (gait_valid 3/6 walk/det, 1/6 walk_startjitter/det) though NOT in sto (5/6, 5/6) -- a partial, mode-dependent version of the family's known leg-drop tendency, not the LEGPARK-SKATE full-quadruped-shuffle pattern (no speed decay, no belly drag, real net progress every episode, only ONE leg ever implicated). Clears the actual canary bar (finite losses, real motion, motor-contract compliance, heading gradient live, no park recapture) -- this is a canary-scope read, not a mature-gait verdict, so the leg-1 caveat is flagged for the acquisition follow-up to watch, not a fail here. Confirms n=3 for the headset-halfgrav heading-canary family (c2/s1/s3 all pass) alongside s1's cleaner read. Next: fund the 40M acquisition continuation (headset-halfgrav-s3acq); its own gate will show whether the leg-1 partial-drop resolves or hardens with budget.

