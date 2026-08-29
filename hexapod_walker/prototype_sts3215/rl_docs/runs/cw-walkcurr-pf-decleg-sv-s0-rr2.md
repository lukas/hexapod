# cw-walkcurr-pf-decleg-sv-s0-rr2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-08-29T16:22:23+00:00

**pod**: hexapod-mjx-train-4

**steps**: 20000000

**parent**: cw-walkcurr-pf-decleg-sv-s0

**hypothesis**: Plain English: can six INDEPENDENT per-leg actor modules discover walking from scratch where every centralized policy froze? (Schilling IROS 2020 decentralization probe, walkcurr wave, seed 0 of 3.) Identical config to cw-walkcurr-pf-decleg-sv-s0/-rr1; the only change is the PENDING_SLOTS 12->40 ring-buffer fix (mjx_backend.py, 59227996) that let this exact config crash at 0 steps twice (s0 LAUNCH_CRASH, rr1 LAUNCH_CRASH -- both before the fix landed). No hypothesis has been tested yet; this is the first attempt that can actually train.

**gate**: Rung-1 gate at 20M: C-env det fixed-forward panel (n>=6) -- zero tilt terminations, cmd_prog_frac >= 0.35, direction_err_deg <= 30, slip/m <= 3.0, gait_valid >= 4/6 with all six legs cycling, real stepping on video. Mid-run discovery litmus: env/walk_freeprog_score must escape the [-0.10,-0.05] static-basin band and trend toward/past 0; escape with rising reward but gate unmet at 20M = continue per 08-21; pinned band + flat/falling reward at 20M = aligned FAIL. Eval-side PASS still enforces the full WALKCURR_PF ranking behaviors (slip is priced at eval regardless of the simple training diet).

**refused_reason**: hexapod-mjx-train-4 already runs cw-walkcurr-pf-decleg-sv-s1-rr2 — GPU pods host exactly one run; pick a free GPU pod.

