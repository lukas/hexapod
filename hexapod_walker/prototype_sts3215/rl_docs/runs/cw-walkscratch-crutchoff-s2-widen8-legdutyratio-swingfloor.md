# cw-walkscratch-crutchoff-s2-widen8-legdutyratio-swingfloor

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-08T12:16:01+00:00

**pod**: hexapod-mjx-train-9

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2-widen8-acq1-legdutyratiofresh-guardfix1

**hypothesis**: 3rd-seed (s2) tie-break for the swing-count-floor lever: s0 showed 3/4 groups jointly improve (CONTINUE signal), s1 showed 0/4 (mechanism-healthy, no efficacy) -- a 1-of-2 split that cannot be pooled. This seed decides whether the swing-floor pairing (>=2 qualifying swings/4s window zeroing a leg's ratio credit if it hasn't actually stepped) is a real 2-of-3 majority effect or a wash, before funding any cont10m off the swingfloor lineage. Same seed4/init-from-s2_widen8/heading/DR/motor cfg as the matched s2 0.30-dose guardfix1 baseline launched alongside it; only the swing-floor keys added.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY, identical gate text to the s0/s1 siblings: (a) post-grace ratio telemetry present/finite; (b) zero new falls vs the matched 0.30-dose s2 guardfix1 sibling; (c) >=3/4 groups jointly improve gait_valid AND slip/progress vs that sibling for CONTINUE; report whether the specific episode-level 'gait_valid recovers, slip worsens' trade the 0.30/0.45 doses showed persists. Short 2M null does not close the lever alone. Read together with s0 (CONTINUE) and s1 (no efficacy): 2-of-3 seeds improving closes this as a real (if modest) lever; 1-of-3 confirms s1 was the outlier direction and the lever is a wash.

