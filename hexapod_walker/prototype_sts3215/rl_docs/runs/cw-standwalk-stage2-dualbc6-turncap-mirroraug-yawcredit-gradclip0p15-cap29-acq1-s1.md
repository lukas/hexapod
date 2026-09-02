# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-acq1-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PARTIAL

**created**: 2026-09-02T09:27:12+00:00

**pod**: hexapod-mjx-train-1

**steps**: 38000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-canary

**wandb_id**: v7x6lxuk

**hypothesis**: Same question as the seed0 twin (cap29-acq1): does training under the raised 2.9A cap let this lineage's best walk-quality+turn-authority checkpoint hold/improve at acquisition scale instead of degrading like the old-cap 38M acq1 did -- checked on seed1 because this lineage's seed1 siblings have historically diverged from seed0 (the gradclip0p15-canary-s1/acq1 pair showed a distinct 44% over-current fall-rate pathology seed0 never hit), so a seed0-only read of the cap fix would not be seed-robust.

**gate**: Same gate as cap29-acq1 seed0: flat-only eval_done_gate_session n>=12 det+sto DR-0+own-DR, zero falls vs durctrl-canary-s1's own teacher-control bar, direction_err_med/slip_per_m_med vs the cap29 zero-training baselines (46.8 deg/3.09); read jointly with seed0 for a seed-robust verdict, not standalone.

**verdict**: Result: seed1 twin of cap29-acq1, same outcome. 38M steps, zero falls (0/32 term, dr0+ownDR), reward quarters 554.4/2029.3/2257.7/2274.5 (healthy, plateaued). Flat-only eval_done_gate_session n=32: direction_err_med 61.1 deg, slip_per_m_med 3.45 -- both worse than the cap29 zero-training baseline (46.8/3.09), matching seed0's result within seed noise (55.5/3.46). Evidence: logs/ckpt_eval/cw_standwalk_stage2_dualbc6_turncap_mirroraug_yawcredit_gradclip0p15_cap29_acq1_s1_donegate_flatonly/session_verdict.json. Why: two independent seeds converging on the same PARTIAL pattern (zero-falls transfers, steering/slip gain does not) makes this a robust conclusion, not seed noise -- pre-registered PARTIAL branch. Next: same as seed0 -- item 2/3 steering-gap arm is the next lever; do not launch a third cap29-training-time seed, the question this pair was built to answer is answered.

