# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-widen8-acq1-legdutyterm1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-07T21:11:46+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-widen8-acq1

**hypothesis**: Plain English: does a new per-LEG minimum-duty TERMINATION (end the episode like a fall if any leg's ground-contact EMA stays below floor for N seconds -- not another per-tick price) repair the already-entrenched chronic front-pair(legs 0/5) sacrifice this seed's own widen8 40M ACQ checkpoint shows, the same pathology 11 independently-designed per-tick price mechanisms (duty_gate/swing_gate/band_gate/gait_gate) already failed to fix? Continuation (--init-from-source) off this seed's own widen8-acq1 checkpoint, single lever added (safety.walk_leg_duty_terminate_s=4.0, floor=0.05, tau=1.0s, grace=3.0s, dedicated reward.walk_leg_duty_terminate_penalty=150 -- everything else byte-identical). Termination (not price) is the validated pattern from hold_min_load_terminate/walk_idle_terminate for exactly this absorbing-state-beats-price failure class; new mechanism bank-proven this cycle (WALKCURR_LEGDUTY_TERM, 4/4 green: bit-exact off, honest six-leg gait runs the full episode untouched, a permanently-sacrificed flag-leg is cut short well inside its own grace+decay+duration arithmetic, dedicated penalty stays well clear of the full anti-suicide term_penalty).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM/BEHAVIOR CANARY (2M continuation): PASS (repair candidate validated, fund full endurance next) if the previously-chronic front leg(s) 0/5 duty recovers to a genuinely used level (>=0.10 sustained, matching the passing-checkpoint low-duty band already measured) in the majority of episodes, gait_valid improves vs this seed's own widen8-acq1 baseline, 0 new falls, and walk_leg_duty_terminate stops firing by the END of the 2M (i.e. the policy actually resolved the pathology rather than just cycling frequent resets). FAIL - MECHANISM if the leg stays chronically parked despite the termination (found some way to satisfy the trigger -- e.g. a brief non-load-bearing contact tap -- without real use), if terminations are still frequent at the end (never converges), or if training destabilizes (reward/other-leg regression, new falls).

**verdict**: CANARY FAIL - MECHANISM: walk_leg_duty_terminate does NOT repair this seed's entrenched front-pair (legs 0/5) sacrifice within the 2M canary. Evidence: gait_valid WORSENS vs this seed's own widen8-acq1 baseline (20/24 -> 12/24 total; walk/det alone 4/6->1/6), and the termination is still firing in 19/24 episodes at the END of training (6/6 det, 4/6 sto, 6/6 startjitter/det, 3/6 startjitter/sto) -- never converging away. Video contact sheet shows near-static robot with legs planted after a brief early step, the same chronic sacrifice pattern repeatedly re-triggering the cutoff rather than being resolved. Reward is still rising (quarters 48->126->180->260) so per 08-21 this alone would license more budget, but the run's own pre-registered FAIL branch ('terminations still frequent at the end = never converges') is unambiguously met, matching sibling s0's already-closed FAIL exactly. Why: the hard per-leg duty termination raises the cost of parking but the underlying incentive gradient toward a front-pair-idle 4-leg stance for rear/diagonal headings is not removed by a bigger stick alone; the policy pays the termination tax repeatedly instead of abandoning the basin within 2M. Next: read s2-widen8-acq1-legdutyterm1 and s0-widenbis180-legdutyterm1 (both pending) to complete n=4 before generalizing.

