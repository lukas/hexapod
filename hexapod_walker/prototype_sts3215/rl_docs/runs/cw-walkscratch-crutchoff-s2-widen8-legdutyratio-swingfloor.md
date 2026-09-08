# cw-walkscratch-crutchoff-s2-widen8-legdutyratio-swingfloor

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS

**created**: 2026-09-08T12:16:01+00:00

**pod**: hexapod-mjx-train-9

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2-widen8-acq1-legdutyratiofresh-guardfix1

**wandb_id**: ffsh89cc

**hypothesis**: 3rd-seed (s2) tie-break for the swing-count-floor lever: s0 showed 3/4 groups jointly improve (CONTINUE signal), s1 showed 0/4 (mechanism-healthy, no efficacy) -- a 1-of-2 split that cannot be pooled. This seed decides whether the swing-floor pairing (>=2 qualifying swings/4s window zeroing a leg's ratio credit if it hasn't actually stepped) is a real 2-of-3 majority effect or a wash, before funding any cont10m off the swingfloor lineage. Same seed4/init-from-s2_widen8/heading/DR/motor cfg as the matched s2 0.30-dose guardfix1 baseline launched alongside it; only the swing-floor keys added.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY, identical gate text to the s0/s1 siblings: (a) post-grace ratio telemetry present/finite; (b) zero new falls vs the matched 0.30-dose s2 guardfix1 sibling; (c) >=3/4 groups jointly improve gait_valid AND slip/progress vs that sibling for CONTINUE; report whether the specific episode-level 'gait_valid recovers, slip worsens' trade the 0.30/0.45 doses showed persists. Short 2M null does not close the lever alone. Read together with s0 (CONTINUE) and s1 (no efficacy): 2-of-3 seeds improving closes this as a real (if modest) lever; 1-of-3 confirms s1 was the outlier direction and the lever is a wash.

**verdict**: CANARY PASS - mechanism healthy, no efficacy (3rd-seed tie-break CLOSES the lever as a wash). Telemetry fires (env/reward_walk_leg_duty_ratio -15.7/-20.2, env/walk_leg_duty_ratio_shortfall 0.105/0.134, finite/nonzero) and 0 new falls/terminations vs the matched 0.30-dose s2 guardfix1 baseline (22/24 gv, 0 terms) -- clauses (a)/(b) of this run's own gate PASS. Clause (c), >=3/4 groups jointly improving gait_valid AND slip/progress, does NOT clear: 0/4 groups improve, matching s1's 'no efficacy' shape rather than s0's 3/4. walk/det actually WORSENS (gv 6/6->5/6, a NEW leg5 sacrifice at the identical episode index that was clean in the baseline, that same episode's own prog/slip also worse: 0.34->0.28m, 17.61->22.13 slip/m -- a straight regression, not the previously-named 'gv recovers via worse slip' trade); walk/sto stays flat (6/6->6/6) with slip/prog both mildly worse (+2%/-5%); walk_startjitter/det stays flat (6/6->6/6) with progress down 23% (1.02->0.79); walk_startjitter/sto stays flat (4/6->4/6) with slip/prog both mildly worse (+2%/-9%). Read together with s0 (3/4 groups improve, CONTINUE signal) and s1 (0/4, no efficacy): this is now 1-of-3 seeds showing improvement, 2-of-3 (s1, s2) showing no efficacy or a mild regression. Per this run's own pre-registered gate text ('1-of-3 confirms s1 was the outlier direction and the lever is a wash'), the swing-count-floor lever (reward.walk_leg_duty_ratio_swing_min_count/_swing_window_s) CLOSES as NOT a reproducible fix for the legduty-ratio-charge slip trade. Do not fund a cont10m off s0 alone or design a 4th seed without a new pricing change; the mechanism code stays in the tree (default off, bit-exact, bank-tested) as a proven-inert-at-this-dose option, not a champion lever. Next open branch for walk_leg_duty_ratio_charge (if pursued) needs a genuinely new design, not another seed/dose of the swing-floor shape.

