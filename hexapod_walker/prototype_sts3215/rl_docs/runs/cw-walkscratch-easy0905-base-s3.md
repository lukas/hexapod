# cw-walkscratch-easy0905-base-s3

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-05T09:46:48+00:00

**pod**: hexapod-mjx-train-5

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-base-s0

**wandb_id**: ggejf5gh

**hypothesis**: Plain English: independent seed 3 of the validated easy-physics base family at acquisition budget (mechanism evidence inherited from the base 2M CANARY PASSes; operator 09-05: identical-except-seed skips re-paying 2M startup). From-scratch 40M, identical to base-s0 except --seed 3. Question: seed-robustness of teacher-free stepping on easy physics.

**gate**: Acquisition milestone at OWN physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Mechanism evidence inherited from the family 2M CANARY PASS; spot-check ~2M in W&B. Not met with signals rising = continue/realign per 08-21; FAIL only on flat v_along+reward at budget or park recapture.

**verdict**: ACQ PASS (5th base-family seed/continuation). Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_base_s3_gate/report.json — 0/24 falls across all 4 scenarios, fwd_dist_m median 4.22-4.96m/20s (0.21-0.25 m/s net, the fastest median-forward reading in the base family so far, >>0.03 bar). gait_valid full 6/6 in walk/sto and 5/6 in walk_startjitter/sto; the two PURE-deterministic blocks (walk/det, walk_startjitter/det) each show a repeatable sacrificed-leg pattern (leg 1 alone / legs [1,4]) that fully resolves once stochastic sampling or start-jitter is present — same class of pure-det-only leg-underuse caveat as halfgrav-s0-c1 this cycle, not a permanent drag. Video (walk_sto_0.png) confirms real forward translation with all six legs cycling, no belly drag. Why: 5th independent base-family PASS (joins s0-c1,s1-c1,s2,s4) — the base recipe question is now extremely well-answered. Next: no further RL budget on the base cell; walkcurr easy0905 budget should concentrate on sde continuations (now 4 running: s0-c4,s1-c2,s2-c2,s3-c1b) and the sdehalfgrav-remcost repair pair.

