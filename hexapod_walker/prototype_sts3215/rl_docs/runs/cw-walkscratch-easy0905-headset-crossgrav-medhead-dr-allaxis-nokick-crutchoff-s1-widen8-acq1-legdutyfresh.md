# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-widen8-acq1-legdutyfresh

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-07T21:57:14+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-widen8-acq1

**wandb_id**: 2oy8dcf9

**hypothesis**: Plain English: 2nd seed of the from-scratch legdutyterm dose disambiguation (see s0-widen8-acq1-legdutyfresh's own hypothesis) -- does having the per-leg minimum-duty TERMINATION present from the START of the 8-way heading-widening training prevent the chronic front-pair (legs 0/5) sacrifice from ever forming, instead of failing to repair it after 40M steps of habit like the just-closed 4/4 FAIL legdutyterm1 retrofit batch? Byte-identical to the original widen8-acq1 40M run (same seed 3, same --init-from the pre-widen8 medhead champion) with only the 5 walk_leg_duty_terminate/_penalty cfg-sets added from step 0.

**gate**: PASS if gait_valid across the 24-episode panel is majority-clean (>=18/24, matching the original pre-widen8/medhead baseline band) with NO chronic single-leg sacrifice recurring across most eval draws, 0 new falls vs the undosed widen8-acq1 baseline, and walk_leg_duty_terminate firing rarely/not-at-all by the end of the 40M. FAIL if the same front-pair (legs 0/5) chronic sacrifice still forms by 40M regardless of whether the termination is firing frequently or has gone quiet.

**verdict**: FAIL per this run's own pre-registered gate: gait_valid 13/24 (det 2/6, sto 5/6, startjitter-det 3/6, startjitter-sto 3/6), below the 18/24 majority-clean bar, AND the front-pair (legs 0/5) chronic sacrifice the gate named as an automatic FAIL is still present — legs 0 and/or 5 sacrificed in 8/24 episodes (det eps 0,1,2,4; startjitter-det eps 1,2,5), the same fingerprint as every prior widen8/widenbis180 arm. walk_leg_duty_terminate is still firing at run end (~160-185 hits per ~15-step log interval in the last logged rows, not quiet) while ep_rew_mean is still rising (quarters 193->435->508->606) — per the 08-21 ruling that alone would argue continue-or-realign, but this run's OWN gate explicitly pre-registered 'chronic front-pair sacrifice by 40M FAILS regardless of whether termination has gone quiet,' so the from-scratch dose does not get a pass on reward-still-rising grounds. Frame strips confirm the mixed picture: some episodes (det ep3/5) show genuine multi-step forward travel with clean footfall, most others show the robot pinned near-stationary with 1-2 legs held off the ground. This is the 2nd of 4 legdutyfresh from-scratch seeds to report (s0 also 12/24 gait_valid with the identical legs-0/5 fingerprint, still unverdicted pending its own assigned cycle) — from-scratch dosing does not repair the chronic front-pair sacrifice any better than the retrofit dose did; the per-leg TERMINATION mechanism (safety.walk_leg_duty_terminate_s) is closing out as a FAIL class pending s2/widenbis180-legdutyfresh's reads. Next lever must leave termination-as-price behind: a true role-aware/heading-conditioned per-leg utilization TARGET (reward shaping toward balanced duty, not a safety cutoff) is the remaining unbuilt structural mechanism.

