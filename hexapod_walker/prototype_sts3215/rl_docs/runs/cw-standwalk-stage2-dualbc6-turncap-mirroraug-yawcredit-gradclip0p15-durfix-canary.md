# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-durfix-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-01T21:07:33+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-canary

**hypothesis**: Plain English: today's flat-only sit->rise->walk->lower DONE-gate session on this exact checkpoint (and its seed1 twin) shows walk-segment over_current terminations clustering within 0.3-2.3s of the walk segment's own start (t=10.0s: seq_end_t_s 10.3-12.3 in 16/22 canary + 21/22 s1 terminations), and even the walk segments that survive barely progress (forward_dist ~0.08-0.1m over a nominal 60s) with course_err_1s_med ~100-109deg / wrong_course_frac ~0.6 -- while every isolated per-mode read used to tune this lineage (probe_turn_authority, the 'purewalk' canary evals, the standard DR-0/own-DR harness) runs short (~10-20s) episode windows, and this checkpoint's OWN training recipe (goal.mode_seq=0.75, default mode_seq_segment_s_min/max=6.0/8.0s inside a flat --episode-seconds=30) never once exposes it to more than ~8 continuous seconds of a single mode. This checkpoint has literally never experienced a continuous 60s walk segment -- the DONE gate's actual requirement -- so every mechanism verdict this campaign made (kl-rollback/value-warmup/yaw-credit/grad-clip) was read through a proxy (short-window turn-authority/purewalk probes) that may not predict the real gate at all. Single coupled lever: widen the sequence-episode segment-length band to reach into the gate's own script durations (mode_seq_segment_s_min/max 6/8 -> 20/60) and extend --episode-seconds 30->90 so a drawn segment can actually run that long before the episode ends, then warm-continue this exact checkpoint 2M steps. Prediction-if-true (duration-mismatch is the driver): this run's own eval_done_gate_session flat-only read (paired against the durctrl-canary matched no-cfg-change control) shows meaningfully fewer near-instant-walk-onset over_current terms and walk progress/slip/direction moving toward the isolated-probe band. Prediction-if-false: terminations keep clustering at the same post-switch offset regardless of what the policy has been trained to sustain, pointing at a state-discontinuity defect in the mode-switch mechanism itself (or a long-horizon reward-pricing problem), not a duration-curriculum gap.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS: eval_done_gate_session flat-only (n=8 min, video), read against the durctrl-canary control at the SAME step count: walk-segment over_current terms drop meaningfully below the 16/22|21/22 baseline AND progress_ratio_med/slip_per_m_med move toward the isolated-probe band (prog>=0.25, slip<=4.0), a gap the control does not close. PARTIAL: some improvement over the control (fewer instant-onset terms or better tracking) without clearing those bars -- fund a longer continuation. FAIL: terminations still cluster within ~2s of the walk-segment switch and/or walk metrics stay at baseline despite the widened duration exposure, matching (not beating) the control -- rules out episode/segment-duration mismatch as the (sole) driver; look at the switch mechanism itself or long-horizon reward pricing next.

