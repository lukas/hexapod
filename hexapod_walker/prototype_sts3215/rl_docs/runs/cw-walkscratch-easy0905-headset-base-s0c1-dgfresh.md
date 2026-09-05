# cw-walkscratch-easy0905-headset-base-s0c1-dgfresh

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T18:33:00+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-base-s0c1

**wandb_id**: 8q0axo9n

**hypothesis**: Both entrenched-checkpoint retrofits of the bank-proven strong-floor walk_duty_gate (floor=0.35,g=1.0) on the base-family marginal-underuse pathology (headset-base-s0c1-dgate2-c1, headset-base-irr-dgate2-c1) just closed 2/2 CANARY FAIL - MECHANISM: the training-time price genuinely engages (walk_duty_gate_factor falls well off 1.0) but 2M steps against an already-40M-entrenched checkpoint does not move the harness det-mode duty at all (flat-to-down), and in 2 additional episodes a marginal leg newly parks. This is the SAME entrenched-vs-fresh split already seen on the (now-closed) gSDE lineage, where duty_gate's bare from-scratch arms (sde-dgfresh-s0/s0b, sdehalfgrav-dgfresh-s0) were never actually compared against a same-recipe no-duty-gate twin on the BASE (non-gSDE, still-open) family -- that comparison has never been run. This canary bakes the identical bank-proven price in from STEP 0 of the exact base-s0c1 2M-canary recipe (same seed=0, same --init-from checkpoint base_s0_c1.zip as the already-landed undosed s0c1 canary, ONLY addition: the 3 duty_gate cfg-sets) to test whether pricing marginal duty before the habit entrenches over a full acquisition avoids the leg-4/leg-1 marginal-underuse pattern the undosed s0c1-acq1 lineage went on to develop -- rather than trying to un-teach it after the fact.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY (2M): env/walk_duty_gate_factor must show real movement (not pinned at 1.0 the whole run -- if pinned, repeats INERT-DOSE and closes fresh-bake as a repair angle too). Compare directly against the ALREADY-LANDED undosed s0c1 canary report (logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_s0c1_gate/report.json: walk/det+sto 12/12 gait_valid, walk_startjitter/det 6/6 sacrifice leg[4], startjitter/sto 5/6 valid): PASS if walk_startjitter/det's leg-4 duty is measurably higher than the undosed twin's (even if not yet gait_valid) with walk/det+sto still >=10/12 valid and no new falls -- evidence pricing-from-scratch changes the mean, not just training-time noise. FAIL if startjitter/det leg duty is unchanged/worse vs the undosed twin, or det/sto validity regresses, or falls appear -- closes duty_gate-from-scratch as a repair lever for this family too (2nd family after gSDE), forcing a genuinely new mechanism design (harder floor + explicit per-leg exploration anneal) before any further duty_gate spend.

