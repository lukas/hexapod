# cw-assistfade-rung1-bcinit-taskonly-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY_PASS

**created**: 2026-09-06T02:49:51+00:00

**pod**: hexapod-mjx-train-7

**steps**: 2000000

**parent**: cw-walkteach-scripted-allhead-canary-r1

**wandb_id**: 5ji1q8ws

**hypothesis**: Plain English: seed replicate of cw-assistfade-rung1-bcinit-taskonly-s0 — the assistance-removal rung-1 ignition question (BC-clone init, task-only PPO, no ongoing anchor/imitation, fixed 0.06 m/s forward, mesh/100Hz DR-0) needs two seeds per the curriculum doc's own gate; single lever vs s0: --seed 0->1, everything else byte-identical. See s0's hypothesis for the full rung-1 rationale and ledger audit.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. IGNITION canary (2M, EASIER_WALKING_CURRICULUM.md behavioral gate; judged JOINTLY with -s0, both seeds must pass): det held-out video/eval on own cfg — sustained forward translation full episode, repeated alternating support transitions, all six legs participating (no permanently planted or unloaded leg), ZERO falls and ZERO safety terminations, progress_ratio >= 0.35. Slip/current recorded, not gated at ignition. PASS both => speed-band hardening + rung-2 anchor-fade design (full intermediate-state bank owed first). FAIL-gait-destroyed => rung 2 slower fade / rung 3 tighter residuals, NOT a reward-dose/architecture retry.

**verdict**: CANARY PASS (mechanism health; ignition bar not yet met -- continuation launched). Task-only PPO from BC init (no anchor) did NOT destroy the gait at 2M, which was rung 1's core fear: gait_valid 24/24 across walk/walk_sto/startjitter det+sto, ZERO falls, ZERO safety terms, sac=[] everywhere, video (walk_det strip) shows level body and all six legs cycling with genuine forward translation. Shortfall is pure speed: det prog med 0.22 (fwd 0.12m/10s at 0.06 m/s cmd) vs the 0.35 ignition bar; slip 8-12/m recorded (not gated at ignition). Reward not flat (quarters 85/111/168/109). Per the 08-21 ruling and the gate's own 'do not judge skill acquisition at 2M' scope this is continue-not-retreat: launched cw-assistfade-rung1-bcinit-taskonly-s1-cont8m (+8M from own checkpoint, ignition bar judged at 10M) plus seed-stability canary -s2 (s0's Q4 reward collapsed 96->23, s1's did not; s2 disambiguates seed-vs-recipe). The JOINT rung-1 ignition read stays open pending s0's gate eval (still running on train-4, owned by the concurrent triage cycle). Retreat branch (rung-2 slower fade / rung-3 residuals) only if cont8m plateaus or siblings show gait destruction -- doc-binding: never a reward-dose/architecture retry on this rung.

