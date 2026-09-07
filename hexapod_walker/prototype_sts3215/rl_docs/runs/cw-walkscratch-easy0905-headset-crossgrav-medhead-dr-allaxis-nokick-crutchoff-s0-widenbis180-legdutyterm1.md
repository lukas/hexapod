# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widenbis180-legdutyterm1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-07T21:16:48+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widenbis180

**wandb_id**: dnpmd5tp

**hypothesis**: Plain English: same repair test as the widen8 trio, on the OTHER already-entrenched instance of this pathology -- the widenbis180 lineage (base5+ONLY the 180deg heading, 40M ACQ, chronic leg-0 sacrifice). Does the new per-LEG minimum-duty TERMINATION (safety.walk_leg_duty_terminate_s, end the episode like a fall if any leg's ground-contact EMA stays below floor for N seconds -- not another per-tick price) repair it? Continuation (--init-from-source) off this seed's own widenbis180 checkpoint, single lever added (safety.walk_leg_duty_terminate_s=4.0, floor=0.05, tau=1.0s, grace=3.0s, dedicated reward.walk_leg_duty_terminate_penalty=150 -- everything else byte-identical). New mechanism bank-proven this cycle (WALKCURR_LEGDUTY_TERM, 4/4 green).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM/BEHAVIOR CANARY (2M continuation): PASS (repair candidate validated) if leg-0 duty recovers to a genuinely used level (>=0.10 sustained) in the majority of episodes, gait_valid improves vs this seed's own widenbis180 baseline (18/24), 0 new falls, and walk_leg_duty_terminate stops firing by the END of the 2M. FAIL - MECHANISM if the leg stays chronically parked despite the termination, terminations stay frequent at the end, or training destabilizes.

