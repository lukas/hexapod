# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-widen8-acq1-legdutyratiofresh-guardfix1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS

**created**: 2026-09-08T00:33:43+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-widen8-acq1

**wandb_id**: tdpmyt9z

**hypothesis**: BUG-FIX RELAUNCH of s1-widen8-acq1-legdutyratiofresh: the operator (commit ebad6d0d, 'Activate standalone leg-duty ratio reward contact tracking') found the original code never added g_ratio to the shared contact-bookkeeping activation guard, so on this recipe (k_park_duty=0, k_step_event=0, no other gate armed) the EMA/bookkeeping block never ran at all -- the charge was SILENTLY INERT (bit-identical to charge=0) despite the cfg saying 150.0. The original s1 run's result is INVALID, not evidence either way. This relaunch uses the fixed code (pulled, 16/16 leg_duty_ratio+adjacent bank tests green incl. the operator's own new activation-guard regression test). Same hypothesis/gate as the original: fresh provenance, 2nd seed, tests whether the additive duty-balance charge stops the chronic front-pair sacrifice.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same as the original s1-widen8-acq1-legdutyratiofresh gate: PASS if the chronic leg's duty recovers (peer-relative ratio >=0.22 majority of episodes) and gait_valid >=18/24 with 0 new falls; CONTINUE if reward+gait_valid both trending up but short; FAIL if the same sacrifice persists regardless.

**verdict**: CANARY PASS (mechanism-health scope): exact corrected guardfix1 24-episode walk/startjitter det+sto gate is21/24 gait_valid,0/24 terminations. Each leg's episode-aggregate peer-relative duty ratio>=0.22 in at least22/24 episodes ([23,24,24,24,24,22]); active GPU charge=-150*shortfall verified at2,097,152steps. THIS DOES NOT ESTABLISH EFFICACY: actual initial checkpoint s1_widen8 also21/24, while same-budget undosed infrastructure-invalid original arm22/24; those original metrics remain usable as an undosed comparison, not evidence of active reward. Single +10M prevention/duration acquisition cw-walkscratch-crutchoff-s1-widen8-legdutyratio-guardfix-acq10m is launching from this corrected output,RNG3,unchanged heading/reward/motor/DR; it tests documented late entrenchment and must retain>=21/24,0newfalls,no new chronic sacrifice. Final walking/joystick qualification remains unmet.

