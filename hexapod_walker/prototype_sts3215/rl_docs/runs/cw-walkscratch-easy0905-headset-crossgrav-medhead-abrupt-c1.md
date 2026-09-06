# cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS - INFORMATIVE (cross-gravity transfer confirmed)

**created**: 2026-09-05T23:42:57+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-medhead-acq1

**wandb_id**: qzcfku3j

**hypothesis**: Plain English: does a hexapod gait that already walks cleanly (six legs, no favoritism) survive an abrupt jump to full real-world gravity, or does the same leg-1/4 favoritism that has now closed 8/8 reward-price mechanisms and the whole gSDE exploration-scheme alternative on the base(1g) family reassert itself? Warm-starts from headset-halfgrav-medhead-acq1, the best mature (40M) leg-healthy halfgrav champion (ACQ PASS, gait_valid 22/24, walk/det 6/6, 0 falls, slip at/under the 2.9 teacher band in 3/4 modes) -- a checkpoint that has NEVER seen 1g gravity -- and abruptly sets ease.gravity_scale=1.0 (full gravity from tick 0) for a 2M-step discovery continuation. This is a genuinely new causal theory, distinct from every mechanism tried so far: all 8 closed reward/state-price mechanisms and the closed gSDE-exploration variant were tested on lineages that trained FROM SCRATCH under 1g and never had a leg-healthy starting point to begin with (even the earliest undosed base(1g) 2M checkpoints already show the leg-4 sacrifice fingerprint in walk_startjitter/det -- see s0c1's own PASS canary notes). If the pathology is a forced consequence of 1g dynamics (actuator torque/current limits, contact loading) regardless of policy quality, this run should degrade toward the identical leg[1,4]-sacrifice fingerprint -- closing the 'bad init/seed' theory for good and confirming the standing reallocate-to-halfgrav conclusion with direct evidence. If the six-leg gait instead holds up (or degrades only mildly and is recoverable with more steps), that opens a completely new cross-gravity curriculum-transfer path for the base(1g) family that no prior mechanism tested.

**gate**: DISCOVERY (2M), abrupt-gravity arm: run the harness (walk+walk_startjitter, det+sto) at ease.gravity_scale=1.0. PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic (<0.10 duty every episode) single-leg sacrifice pattern -- direct evidence 1g walking is reachable via cross-gravity transfer, license a 40M continuation. FAIL/INFORMATIVE-NEGATIVE if gait_valid collapses to the same leg[1,4] chronic-sacrifice fingerprint as the base(1g) family's own closed mechanisms (matching medhead_acq1's 10/24 base-family fingerprint) -- confirms 1g dynamics force the pathology regardless of init quality, closes the cross-gravity-transfer theory, and hardens the reallocate-to-halfgrav conclusion with direct causal evidence. Either outcome is informative; do not require a mature 40M-grade gait at 2M.

**verdict**: Abrupt jump to full 1g (ease.gravity_scale=1.0 from tick 0) on the leg-healthy halfgrav-medhead-acq1 champion (never saw 1g before) does NOT reproduce the base(1g)-family chronic leg-1/4 sacrifice fingerprint that has closed 8 reward-price/state mechanisms + gSDE end-to-end. Harness gait_valid 20/24: walk/det 6/6 CLEAN (sac=[] every episode, duty spread 0.18-0.76 across all 6 legs), walk/sto 6/6 clean, walk_startjitter/det 3/6 + walk_startjitter/sto 5/6 with only a MILD leg-4 softening under added start-pose jitter (duty 0.06-0.14, 47-117 real swings/20s -- nothing like the base family's near-zero-touch entrenchment). 0 falls/terminations in all 24 episodes. Video (walk_det_0, walk_startjitter_det_2 frame strips) confirms genuine six-leg cycling with the body translating, not frozen/dragging. Directly evidences that the base(1g) leg-favoritism pathology is NOT a forced consequence of 1g dynamics for an already leg-healthy policy -- it reopens 1g walking as reachable via cross-gravity curriculum transfer, an alternative to reward-price repair (closed 8/8) or straight reallocation to halfgrav. Per the gate's own pre-registered text this licenses a 40M acquisition continuation; launched cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1 same cycle.

