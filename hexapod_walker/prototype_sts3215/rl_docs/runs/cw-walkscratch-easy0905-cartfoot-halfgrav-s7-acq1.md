# cw-walkscratch-easy0905-cartfoot-halfgrav-s7-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ PASS

**created**: 2026-09-08T09:02:37+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-s7

**wandb_id**: traypy7y

**hypothesis**: Own-checkpoint 40M continuation of the CANARY-PASSed cart_foot (ON) halfgrav+seed7 arm: does the Cartesian foot-target action decode learn real six-leg walking at 0.5g over a full budget, and how does its slip/m compare to the matched joint-space sibling offctrl-s7-acq1 at the SAME fresh-init-then-continued depth? Mirrors the already-proven 1g fork(b) recipe (cartfoot-freshinit-c1-s7-acq1) one gravity cell over.

**gate**: ACQUISITION: >=0.03 m/s median net forward in >=1 of walk/det,sto (0 falls in det), read together with offctrl-s7-acq1 at the SAME budget. PASS/CONTINUE per the 08-21 ruling if reward is still rising; slip/m vs the matched OFF sibling is the headline comparison, not a hardening bar.

**verdict**: Fresh-init Cartesian foot-target ON arm clears the 40M halfgrav acquisition gate cleanly on its own numbers: 0 falls/terminations in 24/24 gate episodes across all 4 groups, speed_mean_m_s 0.189-0.238 (>>0.03 m/s floor) in every episode, gait_valid 6/6 in walk/det, walk/sto and walk_startjitter/sto, 4/6 in walk_startjitter/det (2 episodes sacrifice one leg each, the same startjitter/det fragility already seen on the 1g OFF control -- not new). slip/m med is notably LOW at this gravity (1.56 det / 1.72 sto), well under the 1g cartfoot fresh-init pair's 2.79-3.41 band. Reward quarters rise monotonically [-710.9, 106.6, 888.5, 1143.1], still climbing -- 08-21 ruling satisfied either way since evals already pass outright. Contact-sheet frames show a level body translating with visible alternating leg swing, no flag-leg/skate pathology. This is an ON-ONLY read: the matched offctrl-s7-acq1 sibling (launched same cycle by a concurrent cycle, evidence-gated on this exact ON run) finished training (wandb state=finished, 40370176 steps) but its gate eval was still mid-prestage at read time (owned by that run's own triage cycle per 'holding triage until prestage evals sync' in orchestrator.log) -- do not treat this as a full ON/OFF PARITY close, only as the ON arm's independent PASS. Next: whichever cycle reads offctrl-s7-acq1 closes the halfgrav seed7 pair (expect near-parity slip given the 1g seed7/10/11 cohort's precedent); this cycle is separately extending the halfgrav cohort to seed10/seed11 canaries to match the 1g n=3 practice.

