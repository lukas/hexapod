# cw-assistfade-rung1-bcinit-taskonly-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T02:49:51+00:00

**pod**: hexapod-mjx-train-7

**steps**: 2000000

**parent**: cw-walkteach-scripted-allhead-canary-r1

**wandb_id**: 5ji1q8ws

**hypothesis**: Plain English: seed replicate of cw-assistfade-rung1-bcinit-taskonly-s0 — the assistance-removal rung-1 ignition question (BC-clone init, task-only PPO, no ongoing anchor/imitation, fixed 0.06 m/s forward, mesh/100Hz DR-0) needs two seeds per the curriculum doc's own gate; single lever vs s0: --seed 0->1, everything else byte-identical. See s0's hypothesis for the full rung-1 rationale and ledger audit.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. IGNITION canary (2M, EASIER_WALKING_CURRICULUM.md behavioral gate; judged JOINTLY with -s0, both seeds must pass): det held-out video/eval on own cfg — sustained forward translation full episode, repeated alternating support transitions, all six legs participating (no permanently planted or unloaded leg), ZERO falls and ZERO safety terminations, progress_ratio >= 0.35. Slip/current recorded, not gated at ignition. PASS both => speed-band hardening + rung-2 anchor-fade design (full intermediate-state bank owed first). FAIL-gait-destroyed => rung 2 slower fade / rung 3 tighter residuals, NOT a reward-dose/architecture retry.

