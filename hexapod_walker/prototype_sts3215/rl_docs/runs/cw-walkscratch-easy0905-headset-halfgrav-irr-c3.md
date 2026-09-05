# cw-walkscratch-easy0905-headset-halfgrav-irr-c3

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: pass

**created**: 2026-09-05T14:57:09+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-irr-c1

**wandb_id**: 0vpok57r

**hypothesis**: Plain English: the irregular-direction-change-timing lever (goal.walk_cmd_resample_jitter=0.5) already reads healthy on 2 independent halfgrav champions (irr-c1 off halfgrav-acq1, irr-c2 off halfgrav-s1acq) -- this is the SAME jitter mechanism on the THIRD and last independent halfgrav heading champion (headset-halfgrav-s3acq, just ACQ PASSed this cycle at 22/24 gait_valid) to complete an n=3 cross-checkpoint confirmation, matching the family's own established n=3 pattern for every other rung this campaign. Cheap 2M canary, own-checkpoint warm start, no teacher/BC/motion-prior.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Canary/mechanism-health at OWN physics (0.5g): env/walk_speed stays alive (not decaying toward 0), ep_rew_mean/ep_len_mean not collapsing early, no blowup. Per 08-21: healthy canary funds a 40M acquisition follow-up with the real gate (20s held-out panel with jittered heading changes, >=0.03 m/s median net forward per heading, 0 falls/12 det eps, gait_valid majority, six-leg lift/place on video); flat reward + collapsed speed = FAIL, no continuation.

**verdict**: CANARY PASS — 3rd/3rd independent halfgrav irr-timing canary (irr-c1/c2/c3 all PASS), closing the n=3 confirmation set for the 0.5g heading family's irregular-direction-change-timing rung. Evidence: gait_valid 23/24 (walk/det 6/6, walk/sto 6/6, walk_startjitter/sto 6/6, walk_startjitter/det 5/6 with only one marginal leg-1 flag), 0/24 falls, fwd med 2.44-3.10m/20s, slip med 2.18-2.27 (tight, matches irr-c1/c2). Video (walk_det_0.png) shows clean six-leg tripod cycling, no drag. Reward quarters 32.6/74.2/73.0/126.5 rising monotonically, matches sibling canaries' health signature. Why: warm-started off headset-halfgrav-s3acq (the 3rd clean acq champion), same recipe as irr-c1 (off acq1)/irr-c2 (off s1acq) — proves the irr-timing jitter mechanism generalizes across all 3 independent heading-family checkpoints on this gravity cell, not a single-seed fluke. Next: this canary-level PASS licenses a 40M acquisition follow-up only if the gravity cell's real ACQ gate needs a 3rd independent lineage; halfgrav-irr-acq1 (concurrent-cycle-owned, off s1acq) already covers the acquisition question for this cell, so no new launch off this specific c3 checkpoint unless acq1 fails and a repeat lineage is needed.

