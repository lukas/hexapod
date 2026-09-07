# cw-assistfade-rung4-revhandoff-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-07T07:17:48+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkcurr-phase-sv-contact-s0

**wandb_id**: 0p4y5k91

**hypothesis**: Plain English: if every episode STARTS mid-walk (a real-physics handoff from the scripted tripod teacher, annealing to zero assistance), can the already-refuted phase/contact reward diet finally escape the static-stand basin? Mechanism: goal.walk_reverse_handoff_gate=1 + sched-annealed goal.walk_reverse_handoff_s 2.0->0.0 (t0=0.8M, t1=1.8M, n_envs=4096) on the exact cw-walkcurr-phase-sv-contact-s0 diet -- rung 4 of EASIER_WALKING_CURRICULUM.md, whose own text gates any rung-4 relaunch on exactly this reverse curriculum + matched bank (ASSISTFADE_RUNG4 CPU bank 4/4 green; new MJX bank test_mjx_reverse_handoff 5/5 green incl. sharded-vs-inprocess BITWISE with gate on; legacy MJX suite 24/24 after the sharded knee-frame fix, see assistfade STATUS 09-07 ~07:3x). walk_cmd_hold_s=0/ramp_s=0 arm the tick-0 command so the handoff is a genuine mid-WALK start (measured 0.018 m/s body speed at reset vs 4e-4 step-in-place without). Random init, from-scratch per rung-4 semantics, existing planned seed s0, 2M mechanism-health budget.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH canary (2M): PASS if (a) trains to completion, no NaN/crash, throughput within ~30% of the phase-sv baseline fps (handoff choreography cost); (b) handoff engages (episode starts already-moving on video/eval) and reward is not flat; (c) policy SUSTAINS motion beyond the handoff: walk det prog_ratio at 2M clearly above the historical phase-sv static-basin fingerprint (which was prog~<0.1) or clearly rising, with no march-in-place exploit (phase_agreement>0.8 while prog_ratio<0.2 = FAIL-EXPLOIT). FAIL-MECHANISM if the annealed-hard end reverts to the static basin with reward also flat. Reward rising + weak eval = continue/realign per the 08-21 ruling, never a reflex STOP. Caveat for the reader: DR-0 eval-harness envs sit at sched tick~0 so their resets ALSO run the 2.0s handoff -- judge on measured travel/gait/slip behavior, and compare against the handoff-free CPU baseline if the gate read is ambiguous.

