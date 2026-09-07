# cw-walkcurr-sac-sv-tilt5-s1-b20m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-08-30T04:25:52+00:00

**pod**: hexapod-mjx-train-7

**steps**: 20000000

**parent**: cw-walkcurr-sac-sv-tilt5-s1

**hypothesis**: Plain English: the best-behaving config this whole track has produced (SAC seed 1 + anti-tilt dose 5.0: real six-leg stepping most episodes, forward_dist median 0.055m, dies by stumble not freeze) has only ever trained for 2M steps -- give it 10x. Operator-ordered overnight population sweep (MCP operator lane 20260830T035139Z, bigger budget explicitly fine). Byte-identical config/seed/diet to cw-walkcurr-sac-sv-tilt5-s1 (WALKCURR_SV_TILT bank green at dose 5.0) -- ONLY lever is budget 2M->20M; SAC has no --init-from, so fixed-seed determinism reproduces the first 2M then trains 18M past it (same workaround precedent as sac-sv-s1-budget10m). Key difference from that budget10m FAIL: that raise ran on the NO-tilt diet with zero balance gradient; tilt5 is the one diet where a balance gradient demonstrably changed behavior (5/6 gait_valid, longer stepping before the fall), so budget may compound here where it could not there. Prediction-if-true: fall rate drops below 24/24 and forward_dist clears 0.06m and keeps climbing across the extra 18M, ep_len rising. Prediction-if-false: fall ceiling unchanged at 20M with flat reward -- the budget lever closes on the tilt5 line too, and the fork moves to the structural balance/anti-freeze pretrain curriculum (STATUS candidate 1). Strongest alternative: a fresh tilt5 seed sibling (s2/s3/s4 arms, same wave) both steps AND balances while seed 1 stays stumble-capped -- seed lottery dominates dose and budget.

**gate**: Rung-1 C-env det+sto fixed-forward panel (n>=6 each) at 20M: PASS needs progress_ratio >= 0.35, slip/m <= 3.0, gait_valid >= 4/6, falls on <= 1/6 det episodes. PARTIAL/continue (08-21): fall rate below 24/24 or forward_dist median clearing 0.06m (past tilt5-s1's 0.055m walk/det ceiling) with reward not declining. FAIL: fall rate and forward_dist unchanged at 20M with flat/declining reward. Discovery litmus per the corrected standard: env/walk_speed holding 0.05-0.08 AND ep_len stable/rising AND over_current at background. Selection discipline (operator 08-30): no promotion from the search eval alone -- held-out eval/command seeds plus a replicate seed before any track-level claim.

**refused_reason**: hexapod-mjx-train-7 already runs cw-walkcurr-sac-sv-tilt5-s1-b20m — GPU pods host exactly one run; pick a free GPU pod.

