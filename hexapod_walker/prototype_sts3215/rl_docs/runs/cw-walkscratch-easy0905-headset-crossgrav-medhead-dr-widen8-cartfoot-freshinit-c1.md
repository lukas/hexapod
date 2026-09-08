# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T08:33:15+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**wandb_id**: kl4alitf

**hypothesis**: Every joint-space attempt to add heading diversity to the crutch-off full-DR composite (widen8: 3-seed ACQ FAIL; 19 total reward-mechanism attempts across price/termination/duty-ratio-target classes, ALL CLOSED FAIL) converges on the same chronic single-leg/front-pair sacrifice under the harder 8-way-heading + full-DR regime. Separately, the Cartesian foot-target action space (fork(b), same day, easy0905 no-DR fixed-forward rung) reached slip PARITY with joint-space when trained FRESH, with ZERO reward-mechanism changes -- an action-space inductive-bias effect, not reward shaping. This tests whether that SAME inductive bias (no reward-mechanism changes at all) avoids or mitigates the chronic-sacrifice pathology when applied fresh-init directly to the harder widen8 8-way-heading + full crutch-off DR composite that has defeated every joint-space reward-mechanism attempt so far. 2M canary first (mechanism-viability question), matching every other canary in this campaign; matched fresh-init joint-space control (offctrl sibling) isolates the action-space effect from ordinary fresh-init-on-hard-DR difficulty.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY: read together with the matched offctrl sibling. PASS (mechanism-viable) if reward is rising AND gait_valid is majority (>=4/6) on at least one eval mode with 0 falls on BOTH arms -- only then does a 40M acquisition pair get funded (mirrors forkbs canary-then-acquisition gate). FAIL if the SAME chronic front-pair/single-leg sacrifice fingerprint (legs 0/5 or the L1/L4 middle pair) appears in the majority of det episodes on EITHER arm regardless of reward trend (matches the widen8-acq1-legdutyfresh pre-registered FAIL clause) -- closes the action-space route for this pathology, leaving the still-unbuilt role-aware mechanism as the only lever. This canary answers does training even ignite under the harder composite, not the slip/parity question forkb already answered on the easy rung.

