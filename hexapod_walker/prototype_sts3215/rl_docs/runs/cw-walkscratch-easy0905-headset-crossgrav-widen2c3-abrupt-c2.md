# cw-walkscratch-easy0905-headset-crossgrav-widen2c3-abrupt-c2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T04:25:34+00:00

**pod**: hexapod-mjx-train-9

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-widen2c3-abrupt-c1

**wandb_id**: g8285ntc

**hypothesis**: Plain English: the widen2-c3 walking champion failed its move from half gravity to full gravity once -- rerun the exact same move with a different random seed to learn whether that champion is inherently fragile at 1g or just got unlucky. The crossgrav sweep currently splits widen2 sources 1 PASS (c1) / 1 FAIL (c3) while irr-timing's analogous 1st-seed FAIL (irrwidenc1) was just REFUTED as seed noise by its 2nd seed (irrwidenc2 CANARY PASS 22/24, 09-06 04:09). This twin (same init checkpoint ppo_goal_..._halfgrav_fullhead_widen2_c3_acq1.zip, same abrupt-1g cfg, ONLY the training seed changed, --allow-twin justified as the pre-registered seed-noise discriminator) applies the identical test to widen2-c3. Prediction-if-true (checkpoint fragility): this seed also collapses into the leg[1,4] chronic-sacrifice fingerprint seen in c1's FAIL => widen2-c3's checkpoint sits near the known base-1g structural attractor and widen2-crossgrav durability is source-checkpoint-dependent. Prediction-if-false (seed noise): majority-valid walk/det with no chronic sacrifice, mirroring irrwidenc2 => widen2-crossgrav seed-sensitivity was transfer-run noise, aligning widen2 with every other healthy-source axis. Strongest alternative: a split-mode result (clean walk/det, chronic under startjitter) matching widen2c2b's masked-basin pattern, which would point at margin-above-attractor rather than binary fragility.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY (2M): INFORMATIVE-POSITIVE if gait_valid majority (>=4/6) in walk/det with no chronic (<0.10-duty every episode) single-leg sacrifice -- reads widen2c3-abrupt-c1's FAIL as seed noise (n=1 each way -> discriminated). INFORMATIVE-NEGATIVE if the leg[1,4] chronic fingerprint reappears -- reads the c3 checkpoint as attractor-adjacent/fragile; then no further crossgrav spend on the c3 source and the widen2 crossgrav story rests on c1's lineage. Either outcome informative; do not require mature 40M-grade gait at 2M; over_current rail hits reported separately per the 09-04 uncalibrated-current ruling.

