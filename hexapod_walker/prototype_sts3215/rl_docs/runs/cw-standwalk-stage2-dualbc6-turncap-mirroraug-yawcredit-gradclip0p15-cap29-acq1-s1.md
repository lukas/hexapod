# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-acq1-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-02T09:27:12+00:00

**pod**: hexapod-mjx-train-1

**steps**: 38000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-canary

**wandb_id**: v7x6lxuk

**hypothesis**: Same question as the seed0 twin (cap29-acq1): does training under the raised 2.9A cap let this lineage's best walk-quality+turn-authority checkpoint hold/improve at acquisition scale instead of degrading like the old-cap 38M acq1 did -- checked on seed1 because this lineage's seed1 siblings have historically diverged from seed0 (the gradclip0p15-canary-s1/acq1 pair showed a distinct 44% over-current fall-rate pathology seed0 never hit), so a seed0-only read of the cap fix would not be seed-robust.

**gate**: Same gate as cap29-acq1 seed0: flat-only eval_done_gate_session n>=12 det+sto DR-0+own-DR, zero falls vs durctrl-canary-s1's own teacher-control bar, direction_err_med/slip_per_m_med vs the cap29 zero-training baselines (46.8 deg/3.09); read jointly with seed0 for a seed-robust verdict, not standalone.

