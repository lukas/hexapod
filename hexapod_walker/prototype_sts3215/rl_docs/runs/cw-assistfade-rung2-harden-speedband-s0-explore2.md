# cw-assistfade-rung2-harden-speedband-s0-explore2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T16:39:55+00:00

**pod**: hexapod-mjx-train-0

**steps**: 8000000

**parent**: cw-assistfade-rung2-harden-speedband-s0-lsd2

**wandb_id**: m9vvxa5y

**hypothesis**: Plain English: the -lsd2 pair proved the reward already prices command-tracking speed with a real ~20-24% return gap (probed+banked this cycle) and that log_std genuinely moved (-2.0->-2.98 std~0.135->0.05) -- yet achieved speed still didn't budge across a 2x commanded band. Kernel-width was tested and ruled out (test_harden_speedband_sigma_v_narrowing_does_not_widen_command_gap, 09-06). The remaining untested single-axis lever is exploration MAGNITUDE: -2.0 (std 0.135) may simply not be large enough noise to escape a stride-length pattern entrenched over 10M+ prior steps of single-fixed-speed training. This arm doubles the boost to --warm-log-std-override=-1.3 (std~0.27, still annealing back to the same -3.0 target over the same 8M budget) with everything else byte-identical to -lsd2.

**gate**: PASS if the standard held-out det+sto gate (4 modes) clears gait_valid majority (>=5/6)/0 falls/progress_ratio>=0.35 every mode AND per-episode speed_mean_m_s visibly covaries with cmd_dist_m/10s (not clustered within ~0.005 m/s across a >=0.02 m/s commanded spread). FAIL-COLLAPSE if gait_valid/falls regress vs the -lsd2 parent (bigger noise destabilizing the gait). FAIL-STILL-IGNORES if speed stays flat despite the bigger boost -- this would rule out 'exploration magnitude' too (both the -v2 zero-boost and -lsd2's -2.0 boost and this -1.3 boost all flat) and point at a structural/capability barrier needing either a fresh non-phase-locked init or an explicit stride-amplitude reward term (a genuinely new mechanism, not another log-std value).

