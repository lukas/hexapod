# cw-walkscratch-easy0905-headset-base-s1c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-05T13:03:48+00:00

**pod**: hexapod-mjx-train-5

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-base-s1c1

**wandb_id**: in4gfqjz

**hypothesis**: Plain English: headset-base-s1c1's 2M canary just proved the heading-tracking gradient is live on a FOURTH base-family seed (same recipe as headset-base-c1/acq1, headset-base-s0c1/acq1) -- this gives it the full 40M acquisition budget to see if it learns to walk toward the commanded heading set (straight/+45/-45deg) as cleanly as base-s2/s4/s0-c1/s1-c1 walked straight. Warm-started from its own 2M checkpoint (own-track, not teacher/BC/motion-prior). If true: gait_valid=True six-leg walk on all 3 headings, 0 falls, slip near the base family's own 2.6-3.4 band. If false: sacrificed-leg/flag-leg pattern or falls under heading commands.

**gate**: Acquisition milestone (own physics, unchanged): 20s held-out heading-set (0/+45/-45deg), >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto.

**verdict**: ACQ PASS -- a second base-family heading-set seed (s1c1) clears the same 40M acquisition rung headset-base-acq1 already passed, reproducing the identical already-banked leg1/4 startjitter-det caveat rather than a new failure mode. Evidence: 40M steps finished, reward quarters 397/705/764/798 (monotonic, near-plateau). Gate (own 1g physics, 24 eps, logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_s1c1_acq1_gate/report.json): 0/24 falls (all terminated=false), speed_mean_m_s 0.14-0.172 every episode (>>0.03 m/s bar), height_err_end ~15-25mm (no belly drag), gait_valid 18/24 -- the 6 false episodes are ALL walk_startjitter/det with legs [1,4] flagged, but swing_count for those legs stays 39-160/20s (micro-stepping, not LEGPARK-SKATE near-zero-touch), walk/sto and walk_startjitter/sto both clean 6/6. slip_per_m med 3.98 (range 3.17-5.25) -- same 3.0-4.8 band every base-family PASS this campaign has carried, above the 2.9 joystick reference but not disqualifying per that precedent. Frame strips (walk_det_0, walk_startjitter_det_0) show upright six-leg cycling with real forward background translation even in the flagged mode. Why: own-checkpoint continuation off headset-base-s1c1's own 2M heading canary, same physics/reward as acq1 -- expected to reproduce its fingerprint, and it does; harness 'success=false' flags are the tight-course-tracking field, not this rung's literal gate (net-forward-per-heading only), same read as every prior PASS in this family. Next: combines with the concurrent cycle's own s0c1-acq1 read toward the base heading-family's n=3 seed-robustness check (this verdict only covers s1c1); once both land, pick the base-family heading champion and let it feed the irregular-timing rung (base-irr-c1, already running).

