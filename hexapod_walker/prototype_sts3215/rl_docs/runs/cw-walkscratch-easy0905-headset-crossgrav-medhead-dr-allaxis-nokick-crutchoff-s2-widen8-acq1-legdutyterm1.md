# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2-widen8-acq1-legdutyterm1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-07T21:14:20+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2-widen8-acq1

**hypothesis**: Plain English: does a new per-LEG minimum-duty TERMINATION (end the episode like a fall if any leg's ground-contact EMA stays below floor for N seconds -- not another per-tick price) repair the already-entrenched chronic front-pair(legs 0/5) sacrifice this seed's own widen8 40M ACQ checkpoint shows, the same pathology 11 independently-designed per-tick price mechanisms (duty_gate/swing_gate/band_gate/gait_gate) already failed to fix? Continuation (--init-from-source) off this seed's own widen8-acq1 checkpoint, single lever added (safety.walk_leg_duty_terminate_s=4.0, floor=0.05, tau=1.0s, grace=3.0s, dedicated reward.walk_leg_duty_terminate_penalty=150 -- everything else byte-identical). Termination (not price) is the validated pattern from hold_min_load_terminate/walk_idle_terminate for exactly this absorbing-state-beats-price failure class; new mechanism bank-proven this cycle (WALKCURR_LEGDUTY_TERM, 4/4 green: bit-exact off, honest six-leg gait runs the full episode untouched, a permanently-sacrificed flag-leg is cut short well inside its own grace+decay+duration arithmetic, dedicated penalty stays well clear of the full anti-suicide term_penalty).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM/BEHAVIOR CANARY (2M continuation): PASS (repair candidate validated, fund full endurance next) if the previously-chronic front leg(s) 0/5 duty recovers to a genuinely used level (>=0.10 sustained, matching the passing-checkpoint low-duty band already measured) in the majority of episodes, gait_valid improves vs this seed's own widen8-acq1 baseline, 0 new falls, and walk_leg_duty_terminate stops firing by the END of the 2M (i.e. the policy actually resolved the pathology rather than just cycling frequent resets). FAIL - MECHANISM if the leg stays chronically parked despite the termination (found some way to satisfy the trigger -- e.g. a brief non-load-bearing contact tap -- without real use), if terminations are still frequent at the end (never converges), or if training destabilizes (reward/other-leg regression, new falls).

