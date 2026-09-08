# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-cartfoot-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T05:32:34+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m

**wandb_id**: gzyvhnzt

**hypothesis**: Plain English: the scratch walk champion's ~5-6/m slip floor survived nine slip-pricing reward arms, DR-band narrowing, a torsional-friction dose and the action-clip controllability probe -- the one named remaining structural lever is HOW foot placement is parameterized, so this arm reinterprets the SAME 18 actions as per-leg Cartesian foot targets (leg-root-frame box 6/3.5/4 cm around the source decode's exact a=0 stance-foot point, exact model-derived analytic IK, FK parity 1.8e-16 m; reward/plant/SafetyLayer/motor contract and RNG2 untouched, keys default-off bit-exact) and asks whether the cont40m champion, warm-started with its joint-space skills scrambled under the new action semantics, RE-ACQUIRES walking through the foot-space parameterization in 2M and where its slip lands vs the matched off control. Mechanism evidence: 12/12 local bank (test_cart_foot_decode.py + root's test_cart_foot_frame.py) + root's GPU/Warp env bank PASS (artifacts/rl_watchdog/cart_foot_gpu_bank_20260908, decode parity 0.0 rad under DR/pool restore, hashes == snapshot b24c2ffa). Prior-free: pure kinematic action reparameterization, no clock/teacher/prior.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. 2M canary, standard 24-ep walk/walk_startjitter det+sto gate read AGAINST the byte-identical cartfoot-offctrl control: MECHANISM-VIABLE if 0 falls/terminations and gait_valid >= 18/24 with six-leg cycling on the contact sheet; PROMISING (fund an ACQ continuation) if additionally mean slip_per_m beats the off control in >=3/4 groups; FAIL-MECHANISM if it cannot re-acquire (falls, or gait_valid < 12/24 with reward flat). Per the 08-21 ruling, partial re-acquisition with reward still rising licenses a continuation, not a STOP. A 2M read is acquisition/mechanism evidence, not class closure.

