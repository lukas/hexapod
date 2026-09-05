# standwalk STATUS journal archive — 2026-09-05c (verbatim top block before this rewrite)

Update, 2026-09-05 ~04:5x: **item-1 mechanism BUILT + LAUNCHED:
phase-scheduled multi-teacher, the track's only surviving open lever.**
Every static combined-tick reweight/rescale (combined_skip,
combined_dose, yaw_arm_scale, omega_boost, selective_omega_boost —
the ~20-arm grid closed 09-04/09-05) held ONE fixed target/weight for
the WHOLE run; none varied the target over TRAINING PROGRESS. New
mechanism (`train.bc_anchor_multiteacher_blend`+`_schedule_frac`,
default 0.0/1.0 = legacy bit-exact off): sim_env runs a SEPARATE
persistent scripted-gait clock alongside the walk BC-anchor teacher,
same wall-clock ticks but forward speed always zeroed (the undegraded
pure-turn geometry a combined tick would command if turn-only) — a
first same-object double-query attempt was REFUTED by its own
regression test (TripodGait's EMA smoothing returns a stale dt=0 on a
same-tick 2nd call) before landing on the separate-object design.
`bc_anchor.py` blends the two targets at LOSS TIME (only it knows
`_current_progress_remaining`) ramping 0 -> the knob's value over the
first `bc_anchor_multiteacher_schedule_frac` of progress. 137/137
`rl_move/tests/test_bc_anchor.py` green (10 new). Snapshotted
(`exp/...multiteach-b05`). Launched as a pre-registered 4-arm canary
grid (blend {0.5,1.0} x seed {0,1}, schedule_frac=0.5 mirroring this
recipe's own `--log-std-anneal-frac 0.5`, 2M steps, same
probe_turn_authority gate the whole lever family uses) —
`...-cap29-stdwalklohi-multiteach-b{05,10}{,-s1}`, all 4 VERIFIED
RUNNING (train-2/3/5/+1). Next cycle: triage vs the same comparator
every prior lever in this family used (see `rl_docs/runs/...
-selomegaboost4p0-s1.md` for the exact numbers).

Prior updates (09-04 ~13:2x..09-05 ~04:0x) archived verbatim in
`archive/standwalk_STATUS_journal_2026-09-0{4hh,4jj,4kk,4ll,5a,5b}_
trim.md`.

## Next (as of 09-05 ~04:5x, superseded by this rewrite)

1. Triage the phase-scheduled multi-teacher canary grid (4 arms).
2-4. CLOSED (unchanged, see rewrite for current text).
