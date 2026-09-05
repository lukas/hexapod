# cw-walkscratch-easy0905-base-s1-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-05T09:17:44+00:00

**pod**: hexapod-mjx-train-10

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-base-s1

**wandb_id**: if3jt8v8

**hypothesis**: Plain English: second-seed twin of the base continuation — healthy 2M canary gets its acquisition budget from its own checkpoint. Own-checkpoint 40M continuation of base-s1, zero recipe changes; --activation-fn stripped per plain --init-from restriction.

**gate**: Acquisition milestone at own easy physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, all six legs repeatedly lift/place on video, no belly drag; report sto. Not met with v_along/reward still rising = continue/realign per 08-21 ruling, not auto-FAIL; genuine FAIL only if v_along_cmd and reward_walk are flat at this budget or park recapture.

**verdict**: ACQ PASS (own-checkpoint 40M continuation of base-s1). Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_base_s1_c1_gate/report.json — 0/24 falls across all 4 scenarios (walk/startjitter x det/sto), fwd_dist_m median 2.77-3.96m/20s (0.14-0.20 m/s net, >>0.03 bar), gait_valid 6/6 in 3/4 blocks (walk_startjitter/det 3/6, transient sacrificed leg 1 or 4 under jitter only), no permanently sacrificed leg (min per-leg duty_cycle 0.16-0.26 in walk/det+sto), video (walk_det_0.png) confirms real forward translation with all six legs cycling. Matches the base-s2/s4 fingerprint exactly (same family, same caveat). Why: base family (plain, full 1g, no gSDE) continues to reliably clear the easy0905 acquisition bar. Caveat: slip/prog 2.4-3.4 elevated (paddle/skate quality), gate silent on slip at this rung — not blocking per base-s2/s4 precedent. Next: no further RL budget on this specific checkpoint; base family question is now answered by 3 independent PASSes (s1-c1, s2, s4) — de-prioritize further base-family launches, focus remaining budget on the still-open sde/halfgrav/sdehalfgrav cells.

