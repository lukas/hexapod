# cw-assistfade-rung2-harden-speedband-s0-explore2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL - COLLAPSE

**created**: 2026-09-06T16:39:55+00:00

**pod**: hexapod-mjx-train-0

**steps**: 8000000

**parent**: cw-assistfade-rung2-harden-speedband-s0-lsd2

**wandb_id**: m9vvxa5y

**hypothesis**: Plain English: the -lsd2 pair proved the reward already prices command-tracking speed with a real ~20-24% return gap (probed+banked this cycle) and that log_std genuinely moved (-2.0->-2.98 std~0.135->0.05) -- yet achieved speed still didn't budge across a 2x commanded band. Kernel-width was tested and ruled out (test_harden_speedband_sigma_v_narrowing_does_not_widen_command_gap, 09-06). The remaining untested single-axis lever is exploration MAGNITUDE: -2.0 (std 0.135) may simply not be large enough noise to escape a stride-length pattern entrenched over 10M+ prior steps of single-fixed-speed training. This arm doubles the boost to --warm-log-std-override=-1.3 (std~0.27, still annealing back to the same -3.0 target over the same 8M budget) with everything else byte-identical to -lsd2.

**gate**: PASS if the standard held-out det+sto gate (4 modes) clears gait_valid majority (>=5/6)/0 falls/progress_ratio>=0.35 every mode AND per-episode speed_mean_m_s visibly covaries with cmd_dist_m/10s (not clustered within ~0.005 m/s across a >=0.02 m/s commanded spread). FAIL-COLLAPSE if gait_valid/falls regress vs the -lsd2 parent (bigger noise destabilizing the gait). FAIL-STILL-IGNORES if speed stays flat despite the bigger boost -- this would rule out 'exploration magnitude' too (both the -v2 zero-boost and -lsd2's -2.0 boost and this -1.3 boost all flat) and point at a structural/capability barrier needing either a fresh non-phase-locked init or an explicit stride-amplitude reward term (a genuinely new mechanism, not another log-std value).

**verdict**: Result: bigger exploration magnitude (--warm-log-std-override=-1.3, ~2x -lsd2's boost) destabilized this seed's gait outright, worse than sibling s1-explore2 and worse than either weaker-boost predecessor. Evidence: held-out det+sto gate (4 modes, n=24) reads gait_valid 0/6 on EVERY mode (walk/det, walk/sto, walk_startjitter/det, walk_startjitter/sto), sac=[0,1] (two chronically sacrificed legs) in 23/24 episodes, slip/m med 11.8-14.5 (vs the -lsd2 parent's clean 6/6 gait_valid and much lower slip), fwd/prog collapsed to 0.04-0.19 range -- video confirms a near-static splayed-leg pose across all 6 sampled det frames (walk_det_0_sheet.png), matching the pre-registered FAIL-COLLAPSE branch, not a speed-tracking read (gait itself is broken, so the speed-covariance question is moot here). This is consistent with the run's own mid-training canary auto-stop at 4.37M ('protected skill(s) [hold] failed 3 consecutive probes') -- the auto-stop correctly flagged real damage, not noise. Why: matches sibling s1-explore2's independently-verdicted FAIL-COLLAPSE (gait_valid regressed to 2-5/6 per mode, 21/24 over_current terminations) -- 2/2 seeds at this boost level collapse, s0 more severely (full 0/6 across all modes vs s1's partial regression). Combined with -v2 (zero boost, flat-not-collapsed) and -lsd2 (real boost, flat-not-collapsed): exploration MAGNITUDE is now closed 3/3 as a repair lever for the speed-band-ignoring pathology -- the smaller boosts leave the gait intact but don't fix speed-tracking, the bigger boost breaks the gait without fixing it either. Next (per s1's own verdict): a structural/capability lever, not a 4th log-std value -- redo the rung-2 anchor-fade IGNITION itself under the widened 0.04-0.08 m/s band from step 0 (off each seed's original pre-reseed canary checkpoint), testing whether the flat-speed pathology traces to 8M+ steps of single-fixed-speed habituation baked in before hardening ever saw a varying command. Evidence: logs/ckpt_eval/cw_assistfade_rung2_harden_speedband_s0_explore2_gate/{report.json,walk_det_0_sheet.png}, W&B m9vvxa5y.

