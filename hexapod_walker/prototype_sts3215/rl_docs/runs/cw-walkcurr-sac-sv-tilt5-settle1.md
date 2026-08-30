# cw-walkcurr-sac-sv-tilt5-settle1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-08-29T23:38:43+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkcurr-sac-sv-tilt5-s1

**wandb_id**: psvf22ed

**hypothesis**: Plain English: does giving the policy a free 0.5s (ramping to full price over the next 0.5s) grace window on the anti-tilt charge right after spawn let dose=5.0 (the best-so-far SAC anti-tilt dose -- real monotone stepping improvement over dose=2.0, forward_dist_m med 0.055m/gait_valid 5/6, but still 24/24 falls) push past its own ceiling? Root-cause chain from cw-walkcurr-sac-sv-tilt10-s1-r2's FAIL (this cycle): raising the SAME charge from 5.0->10.0 REVERSED the response (gait_valid regressed 5/6->0/6, deterministic instant tilt_pitch collapse) instead of continuing to improve it -- consistent with the charge taxing the exact post-spawn ticks where a stumble-recovery motion is needed most and is least trained, not with genuinely better balance. IDENTICAL SV diet/seed(1)/algo(SAC)/budget(2M)/dose(5.0) as cw-walkcurr-sac-sv-tilt5-s1 -- only lever added: reward.tilt_settle_grace_s=0.5 + tilt_settle_ramp_s=0.5 (new mechanism, env.py compute_reward's tilt_settle_scale, default 1.0=off=bit-exact; WALKCURR_SV_TILT_SETTLE bank built+green this cycle, 4/4: default-off bit-exact, travel still beats every stationary form, wrong-way still below standing, topple still the strict floor at full dose 10.0 with the window on). SAC has no --init-from support (train_ppo_mjx.py refuses it for --algo sac) so this is a fresh 2M run, not a continuation -- the only valid way to add a reward lever to this lineage. Prediction-if-true: fall rate drops below 24/24 and/or forward_dist_m median clears past 0.055m/~0.06m -- the settle window is the missing piece, promote toward the rung-1 bar and consider it default for the dose10 sibling too. Prediction-if-false (window too short/mechanism doesn't help): forward_dist/gait_valid stay in the same 0.05-0.06m/5-6-of-6 band as the unwindowed tilt5 -- the window doesn't move the needle, dose+settle-window class closed, escalate to the operator's terrain-diversity fallback (b) or a structural per-tick balance curriculum. Prediction-if-worse: the free window gets exploited as a topple-during-grace shortcut (forward_dist/gait_valid regress below tilt5) -- window mechanism itself is broken, refine (shorter grace, or gate by qvel/contact state instead of a flat clock) before retrying.

**gate**: Rung-1 C-env det+sto fixed-forward panel (n>=6 each) at 2M, same harness as tilt2/tilt5/tilt10: PASS/continue-worthy needs fall rate below 24/24 det+sto OR forward_dist_m median clearing past tilt5's own 0.055m det ceiling. Compare directly against tilt5-s1 (same dose, no window): improved fall-rate/forward_dist/gait_valid = the settle window is a real lever, promote and consider retrofitting it onto other doses; flat/same = window doesn't help at this dose, close the lever; worse (regression toward tilt2/tilt10's deterministic-instant-fall signature) = window is being exploited or actively harmful, do not retrofit blind.

**verdict**: FAIL -- the settle-window mechanism is a no-op at dose 5.0, not a real lever. Pooled across all 24 held-out episodes (walk/walk_startjitter x det/sto): forward_dist_m median 0.051m, gait_valid 21/24 -- statistically indistinguishable from tilt5-s1's own no-window sibling (0.051m, 20/24). The window did change the FAILURE MODE (over_current terminations 12/24 -> 0/24, all 24 now die via tilt_pitch/tilt_roll instead) but not the outcome: fall rate stays 24/24 in both, and the specific walk/det sub-mode this arm's own pre-registered gate compares against tilt5-s1's '0.055m det ceiling' actually REGRESSES to 0.033m (though gait_valid on that same sub-mode improves 5/6->6/6 -- a genuine mixed/wash result, not a clean win either way). ep_rew_mean quarters [163.7,146.9,146.5,150.4] -- flat-to-declining, not rising: 08-21 ruling says aligned FAIL, not a continue. Evidence: logs/ckpt_eval/cw_walkcurr_sac_sv_tilt5_settle1_gate/report.json (pooled fwd_med/gait_valid recomputed this cycle from the raw per-episode json).

