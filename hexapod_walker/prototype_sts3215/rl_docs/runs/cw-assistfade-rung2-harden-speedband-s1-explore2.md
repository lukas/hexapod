# cw-assistfade-rung2-harden-speedband-s1-explore2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL - COLLAPSE

**created**: 2026-09-06T16:38:40+00:00

**pod**: hexapod-mjx-train-1

**steps**: 8000000

**parent**: cw-assistfade-rung2-harden-speedband-s1-lsd2

**wandb_id**: 6ipzl1ia

**hypothesis**: Twin of s0-explore2: the -lsd2 pair proved the reward already prices command-tracking speed with a real ~20-24% return gap (probed+banked this cycle, test_harden_speedband_sigma_v_narrowing_does_not_widen_command_gap) and that log_std genuinely moved (-2.0->-2.98) -- yet achieved speed still didn't budge across a 2x commanded band. Kernel-width was tested and ruled out. Untested single-axis lever remaining: exploration MAGNITUDE. This arm doubles the boost to --warm-log-std-override=-1.3 (std~0.27) from the SAME seed-1 entrenched checkpoint (cw-assistfade-rung2-anchorfade-s1-reseed8m-gatefix), everything else byte-identical to -lsd2.

**gate**: Same as s0-explore2: PASS if held-out det+sto gate clears gait_valid majority/0 falls/progress_ratio>=0.35 every mode AND achieved speed covaries with cmd_dist_m across episodes. FAIL-COLLAPSE if gait/falls regress vs -lsd2. FAIL-STILL-IGNORES if speed stays flat despite the bigger boost -- rules out exploration magnitude as a lever (3/3: zero-boost -v2, -2.0 -lsd2, -1.3 here all flat) and points at a structural/capability barrier (fresh non-phase-locked init or an explicit stride-amplitude reward term) for the next cycle.

**verdict**: Held-out det+sto 4-mode gate collapsed vs its -lsd2 parent: gait_valid fell to 4/6,5/6,3/6,2/6 (walk/det,walk/sto,startjitter/det,startjitter/sto; -lsd2 was 6/6 clean on all 4 modes), 21/24 episodes now terminate mid-clip via over_current with roll_class=fell (video-consistent fall, -lsd2 had 0/24 terminations), and slip degraded to 3.9-6.5/m (vs 2.4-3.6/m on -lsd2) -- exactly the pre-registered FAIL-COLLAPSE branch. The original target pathology is ALSO unrepaired on top of the collapse: speed_mean_m_s still clusters 0.033-0.048 m/s regardless of cmd_dist_m spanning 0.044-0.53m across episodes (a >10x range), so doubling the exploration boost (--warm-log-std-override=-1.3, std~0.27 vs -lsd2's -2.0/std~0.135) bought zero speed-tracking gain while destabilizing balance recovery into falls. Sibling s0-explore2 independently corroborates the same direction (its own training-time canary auto-stopped at 4.37M citing 'protected skill(s) [hold] failed 3 consecutive probes'); s0's held-out gate report is still mid-eval on train-0, not ready this cycle -- read it before treating this as fully 2/2 confirmed. Why: this closes exploration MAGNITUDE as a repair lever for the speed-band-ignoring pathology -- zero-boost (-v2), +1.65 boost (-lsd2, confirmed real log_std movement via wandb_history), and +2x boost (-1.3 here) all fail to produce speed covariance, and the largest boost actively destabilizes gait. What's next: per this arm's own pre-registered escalation, move to a structural/capability lever instead of a fourth log-std value. Launching the untested no-new-code option first: redo the rung-2 anchor-fade IGNITION itself (not just the late hardening retrofit) under the widened 0.04-0.08 m/s band from step 0, off each seed's original pre-reseed canary checkpoint, to test whether the flat-speed pathology is caused by 8M+ steps of single-fixed-0.06-m/s habituation during ignition before hardening ever sees a varying command.

