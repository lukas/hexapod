# cw-assistfade-rung2-harden-speedband-s1-explore2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T16:38:40+00:00

**pod**: hexapod-mjx-train-1

**steps**: 8000000

**parent**: cw-assistfade-rung2-harden-speedband-s1-lsd2

**wandb_id**: 6ipzl1ia

**hypothesis**: Twin of s0-explore2: the -lsd2 pair proved the reward already prices command-tracking speed with a real ~20-24% return gap (probed+banked this cycle, test_harden_speedband_sigma_v_narrowing_does_not_widen_command_gap) and that log_std genuinely moved (-2.0->-2.98) -- yet achieved speed still didn't budge across a 2x commanded band. Kernel-width was tested and ruled out. Untested single-axis lever remaining: exploration MAGNITUDE. This arm doubles the boost to --warm-log-std-override=-1.3 (std~0.27) from the SAME seed-1 entrenched checkpoint (cw-assistfade-rung2-anchorfade-s1-reseed8m-gatefix), everything else byte-identical to -lsd2.

**gate**: Same as s0-explore2: PASS if held-out det+sto gate clears gait_valid majority/0 falls/progress_ratio>=0.35 every mode AND achieved speed covaries with cmd_dist_m across episodes. FAIL-COLLAPSE if gait/falls regress vs -lsd2. FAIL-STILL-IGNORES if speed stays flat despite the bigger boost -- rules out exploration magnitude as a lever (3/3: zero-boost -v2, -2.0 -lsd2, -1.3 here all flat) and points at a structural/capability barrier (fresh non-phase-locked init or an explicit stride-amplitude reward term) for the next cycle.

