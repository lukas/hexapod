# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-transwin-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-07T18:54:02+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-footslip-c1

**wandb_id**: x5r1ktgp

**hypothesis**: Plain English: the 5 flat/uniform slip-pricing arms tried so far (footslip-c1, loadslip-c1, loadslip-windowed x2, footslip-c1-lowdose) all CLOSED without moving held-out slip/m because they price the whole loaded stance at one flat rate, but a phase-binned audit (rl_docs/tracks/walkcurr/STATUS.md 09-07 ~18:2x, zero training spend) found slip actually concentrates ~50-60% higher in two short windows -- touchdown impact and pre-liftoff drag -- with flat mid-stance in between; a charge that ONLY targets those two windows should move the metric where the flat charges spent most of their budget on already-cheap mid-stance ticks. Single-lever swap vs the byte-identical footslip-c1 recipe on the SAME frozen cont40m champion: turn the closed k_foot_slip_tangent OFF (0.0) and arm the new reward.k_walk_transition_slip=35.0 (deadband 0.015 m/s, cap 0.25 m/s -- same units/dose as the closed uniform lever for a fair comparison) with contact_n=2.0 (matching footslip-c1's own dose), td_ticks=3 (touchdown tick + 2 live follow-on ticks), lo_ticks=3 (trailing retrospective window paid at liftoff, no lookahead). Bank-proven (test_task_semantics.py, 7/7 new tests green, snapshot pending): bit-exact off, deadband gate genuinely gates, fires on real scripted-gait contact dynamics (not just a trained exploit), window width is monotonic, charges LESS total than the matched-dose uniform lever on the same clean gait (confirms it is structurally narrower, not a renamed copy), and preserves every safety ordering (gait clearly beats stall/park, skate stays the clear worst outcome) at the bank dose.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY, not a skill-acquisition or behavior-class verdict. PASS if wandb_history shows env/reward_walk_transition_slip (or walk_transition_td_events/lo_events) trending down or stable while reward_walk/reward_walk_prog stay flat-to-rising (08-21-aligned), AND a fresh own-pod gate re-eval (DR-0, walk+walk_startjitter, det+sto, n>=24) reads 0 falls / gait_valid all-clear (no new leg-sacrifice vs the 22/24 baseline) with slip/m median MEASURABLY lower than the 5.065 training-diet baseline (not another ~4% wiggle) AND no belly-flop/crouch/reduced-contact exploit (env/walk_contact_meaningful_feet stays high, height/roll/pitch stay in the champion's normal band). FAIL-STILL-STUCK if slip barely moves again despite the phase-targeting -- escalate past reward-shaping on this checkpoint to either a bigger dose/wider window or a structural (non-reward) fix. FAIL-EXPLOIT if a crouch/reduced-contact pattern appears.

