Update, 2026-09-03 ~09:4x (idle-kick): **item 0 CLOSED, both seeds
PASS (own-scope) on the real video-bearing flat-only donegate session**
(n=128 ep each, train-6/7): `stdwalklohi-acq1` dir_err_med 44.56deg/
slip_med 2.819, `-s1` 43.6deg/2.939 — BOTH beat the cap29 baseline
(46.8deg/3.09), sto/det progress_ratio convergence holds at full 38M
scale (94-107% of each other) — the arm's own PASS bar, cleared. Zero
falls/256 episodes, gait_valid 1.0. NOT the track DONE gate: dir_err
still misses the ~40deg reference, slip sits at the 2.9 cap — steering
(item 1) is the sole open item. New reference band: 44-45deg/2.8-2.9
slip. SKILLS.md updated.

**Also found+fixed a fleet-wide infra blocker while refilling item 1**
(full account `OPERATOR_QUESTIONS.md` 09-03 ~09:3x): the 09-02 ~22:0x
operator merge's `require_checkpoint_joint_contract` rejects EVERY
checkpoint predating it — including this lineage's own ancestor and
champions — silently blocking ALL warm-starts fleet-wide. Confirmed
the action<->joint mapping itself never changed (pose-literal fixes
only), so backfilling is safe. Built+tested
`rl_move.sim.stamp_legacy_checkpoint` (3/3 green, bit-exact weights),
ran it fleet-wide (1128 stamped, 3 already-current, 0 refused).

**Refilled item 1** (09-02 dig-in lead: worst `course_speed_ratio`
dips land at the eval diet's ~4s `walk_cmd_resample_s` boundaries,
training only ever used a slower 6s/jitter-0.2 diet) — launched a
2-seed 2M canary `cap29-stdwalklohi-resamplematch-canary{,-s1}` (one
lever: match train-time `walk_cmd_mode=stress_mix`/`resample_s=4.0`/
`jitter=0.5` to the eval diet), warm-started from the re-stamped
ancestor. VERIFIED RUNNING (train-1/train-2 — `-s1` is ledger-named
`...-turndiet-canary-s1`, a naming artifact, same cfg). Gate:
`probe_turn_authority` wz_med >=0.07; det+sto walk read under the
matched diet vs this cycle's own baseline (44.56/43.6deg dir,
2.82-2.94 slip) — PASS if dir/course_err drops >=20% clean; PARTIAL
if authority+zero-fall hold but steering doesn't move; FAIL if
authority regresses or terminations appear.
