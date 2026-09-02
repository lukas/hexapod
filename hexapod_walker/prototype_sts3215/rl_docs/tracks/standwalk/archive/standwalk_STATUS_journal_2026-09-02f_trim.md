Update, 2026-09-02 ~15:3x (idle-kick, zero-compute root-cause dig +
4-way canary launch on the det/sto walk-progress asymmetry flagged
last cycle): **config archaeology on the cap29-acq1{,+s1} launch args
+ cached W&B history found a concrete, untested cause candidate.**
Only the STANCE core's log_std is annealed down this whole lineage
(`--log-std-anneal-core stance --log-std-final -4.0`, confirmed live
in `log_std_anneal/stance/std` dropping to 0.0183 by 10% of training);
the WALK core's log_std is never touched by the anneal and its
`train/std` metric sits flat at 0.222-0.223 (log_std≈-1.5) for the
*entire* 38M-step run — i.e. walk-mode action noise never shrinks
while stance's does, a structural asymmetry that lines up with the
det/sto walk-progress gap being far worse than any stance-mode
degradation. This is NOT the same question the already-closed
`stdwalk-mild/hi` canary answered (08-31, dualbc5 lineage): that pair
RAISED walk log_std (-1.5→-0.8/-0.2) chasing turn authority and found
achieved body-yaw noise completely insensitive to input std — refuted
in that direction only. Lowering walk's log_std (this cycle's lever)
is the untested opposite move, and per that same 08-31 finding should
be safe for turn authority (already shown std-insensitive) while
plausibly tightening the walk policy's own sto-vs-det consistency.
**Launched a 2-dose x 2-seed canary grid (2M steps each, cap=2.9,
warm-started from the SAME `gradclip0p15-canary` 2M ancestor cap29-
acq1 itself used, not the degraded 38M checkpoint)**:
`cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-
cap29-stdwalklo-{mild,hi}{,-s1}` — mild anneals walk log_std to -2.0,
hi to -3.5, both paired with stance's existing -4.0
(`--log-std-anneal-core walk,stance --log-std-final <X>,-4.0`, the
multi-core anneal tool built 08-31 for exactly this kind of per-core
schedule, `test_log_std_anneal_multi.py` reconfirmed green pre-
launch). All 4 VERIFIED RUNNING (train-2/3/4/5). Not a reward/task-
mechanism change (pure PPO exploration schedule, no reward-pricing
touched) so `test_task_semantics.py` was not required as a
precondition. Gate (pre-registered, full text in the ledger): (1)
`probe_turn_authority` wz_med stays >=0.07 rad/s (no turn-authority
regression); (2) det+sto `eval_checkpoint.py` walk-mode read shows
sto `progress_ratio_med` rise materially off the cap29-acq1 baseline
(0.045-0.085) toward det (0.32-0.38) without det itself dropping
outside 0.28-0.40 or slip rising. Not yet read (still training this
cycle). Evidence once read: `logs/ckpt_eval/turn_probe_stdwalklo_
{mild,hi}.json`, `logs/ckpt_eval/purewalk_stdwalklo_{mild,hi}_{det,
sto}.json` (paths to be created by the reading cycle).

Update, 2026-09-02 ~15:0x: **cap29-acq1 pair's flat-only
`eval_done_gate_session` READ (n=32 each), both verdicted PARTIAL.**
Zero falls held (0/32 term each, matches the `durctrl-canary` bar —
the training-time cap-raise does NOT regress fall-safety) but
direction_err_med/slip_per_m_med came in WORSE than the cap29
zero-training baseline (acq1 55.5°/3.46, s1 61.1°/3.45, vs baseline
46.8°/3.09) — two seeds agree, not noise. Evidence:
`logs/ckpt_eval/cw_standwalk_stage2_dualbc6_turncap_mirroraug_
yawcredit_gradclip0p15_cap29_acq1{,_s1}_donegate_flatonly/{dr0,owndr}/
report.json` (+ pulled to `/tmp/pull_acq1{,s1}` for the windowed
re-analysis below).

**Deeper zero-compute read of the SAME artifacts** (built the tool
first): `eval_mixed_session.aggregate_session` did not surface the
already-computed windowed course metrics (`eval_checkpoint.
windowed_course_stats`, the operator's 08-29 PRIMARY command-following
read, fb_20260829T141858_9421cd) at the session level — every prior
standwalk session triage had to hand-dig report.json for it. Fixed:
`walk.course_err_{1s,2s}_med_deg` / `course_speed_ratio_1s_med` now
ride along in every `aggregate_session` output, INFORMATIONAL ONLY
(gate.soft unchanged, bit-exact when the source report predates the
field — `test_eval_mixed_session.py` 11/11 green). Reading it back on
this pair:
- windowed course_err (acq1 22.0°, s1 23.2°) is BELOW the tick number
  but still ~2x the joystick-track's calibrated windowed allow
  (2.0+10=12°) — the steering gap is real by either metric, this is
  NOT the "false fail" shape 08-29 found elsewhere (tick 45-55°/
  windowed 2-9°); here windowed stays elevated too.
- **Bigger finding: det vs sto asymmetry dominates the gap more than
  steering does.** Per-episode: DET walk segments with a real command
  (`cmd_dist_m` 4-4.7m) reach `progress_ratio` ~0.32-0.38 (real, if
  ~65% underspeed) with slip 2.8-3.6 — plausible. STO walk segments
  with the SAME command scale reach `progress_ratio` only 0.045-0.085
  (5-8% of commanded distance!) with slip 10.6-28.5 — action-sampling
  noise during walk is closer to non-functional than "degraded."
  Per-window course_speed_ratio_1s on the worst DET windows goes
  slightly negative (-0.05) at exactly the ~4s `walk_cmd_resample_s`
  boundaries — consistent with (not a new refutation of) the closed
  turn-authority-ceiling finding: command changes outrun the policy's
  turn rate, and the DONE-gate's stress_mix diet resamples direction
  every ~4s by design.
- 14/32 session episodes had `cmd_dist_m=0.0` (a stress_mix command
  that sampled near-zero net displacement that segment) and correctly
  contribute no walk metrics — not a bug, not silently inflating the
  medians either way.

Earlier 09-02 updates (~10:4x cap29-acq1 training-finish note, ~09:3x
cap29 acquisition launch + current-confound re-probe CLOSED) moved
VERBATIM to `archive/standwalk_STATUS_journal_2026-09-02e_trim.md`
(purewalk cap29 det baselines: gradclip0p15-acq1 prog 0.35/slip 2.81,
klrolltight-acq1 prog 0.36-0.39/slip 2.74-3.16 — referenced above).


---
(Appended 09-02 ~16:5x, verbatim record of the two per-cycle Update
blocks before they were merged/condensed in STATUS.md for the
80-line-ish budget — the merged summary lives in STATUS.md itself.)

Update, 2026-09-02 ~16:4x (canary grid READ -- `hi`/`hi-s1` CANARY
PASS, acq-scale pair funded): stdwalklo-{mild,hi}{,-s1} 2M grid
(archived below) finished. This cycle's assignment was `hi`/`hi-s1`;
`mild`/`mild-s1` are a concurrent cycle's (own RL_LOG lines, not
duplicated here). Both `hi`/`hi-s1` **CANARY PASS-for-acquisition**,
strongest of the grid: `probe_turn_authority` wz_med 0.19-0.21 rad/s
(both seeds/signs, floor 0.07) -- untouched. `purewalk` det-vs-sto
walk `progress_ratio_med`: hi 0.32/0.32, hi-s1 0.32/0.28 -- STO
essentially MATCHES det on both seeds, closing the cap29-acq1 session
baseline's sto/det gap (0.045-0.085 sto vs 0.32-0.38 det) almost
completely (well past the ~0.15 PASS bar); slip flat-to-better in sto.
Zero falls, 32/32 episodes. (`mild`'s -2.0 dose was weaker: sto
0.14-0.16, right at the PASS floor, worse slip -- `hi`'s -3.5 is the
clear winner.) Confirms the WALK core's un-annealed log_std was the
sto/det-gap driver, not credit assignment/command-resample dynamics.

**Funded the acq-scale follow-up**: respec'd both `hi` canaries to
the full 38M-step budget on the SAME recipe as `cap29-acq1` itself
(one lever changed) -- `...cap29-stdwalklohi-acq1{,-s1}`, VERIFIED
RUNNING train-6/7. Gate: flat-only `eval_done_gate_session` n>=12
det+sto DR-0+own-DR vs the cap29-acq1 baseline (46.8 deg/3.09; acq1
itself came in worse at 55.5-61.1/3.45-3.46) -- PASS if steering+slip
drop to/below baseline AND sto/det convergence survives at session
scale; PARTIAL if falls+convergence hold but steering doesn't
(separate defect, Next item 1); FAIL if sto regresses at scale.
Evidence: `logs/ckpt_eval/{turn_probe,purewalk}_..._stdwalklo_
{hi,hi_s1}*`.

Update, 2026-09-02 ~16:5x (grid closed -- `mild`/`mild-s1` own-cycle
read, CANARY FAIL - MECHANISM both seeds, joint dose-response with the
already-PASSED `hi`/`hi-s1` above): this cycle's assignment was
`mild`/`mild-s1` (the `hi` pair above is a concurrent cycle's own
verdict, not re-derived here, cross-checked for the dose comparison
only). Ran the same two instruments (own cfg, controller CPU,
`--dr-scale 0.2` to match the lineage's own ancestor baseline
methodology — `purewalk_gradclip0p15_acq1_cap29_det`: prog 0.35/slip
2.69). `probe_turn_authority` wz_med 0.189-0.190/-0.198 to -0.204
(both seeds) — clears the 0.07 floor with room to spare, statistically
identical to `hi`'s 0.194-0.209/-0.203 to -0.213: turn authority is
unaffected by seed OR dose, confirming (again) it's not the failure
mode. `purewalk` det/sto: mild det prog 0.35-0.37/slip 3.85-4.23
(healthy progress, slip +40-55% over the 2.69 ancestor baseline); sto
prog 0.11-0.13/slip 9.48-9.83 — only 1.3-2.9x the OLD session-baseline
sto ceiling (0.045-0.085) and just 31-36% of this run's OWN det
progress, missing the gate's own "~0.15+" PASS-for-acquisition bar on
BOTH seeds. Contrast with `hi`: sto 0.28/0.28, 78-90% of det, clearing
0.15 with room. Clean 2-seed-per-arm dose-response, not noise: -2.0
(mild) is on the right side of the mechanism (real improvement over
flat-std) but under-shoots the threshold; -3.5 (hi) clears it. No
further spend on the -2.0 dose — the campaign's next step
(`stdwalklohi-acq1{,-s1}`, full 38M budget) is already funded and
RUNNING (train-6/7) on the winning `hi` dose only. Evidence:
`logs/ckpt_eval/{turn_probe,purewalk}_..._stdwalklo_mild{,_s1}*`.

---
(Appended 09-02 ~18:3x, verbatim record of the merged 16:5x
grid-close Update block before STATUS.md compacted it further.)

Update, 2026-09-02 ~16:5x (4-way stdwalklo-{mild,hi}{,-s1} 2M canary
grid CLOSED, split across two concurrent cycles): the grid tested
whether annealing the WALK core's log_std down (paired with stance's
already-proven -4.0) closes the sto-vs-det walk-progress asymmetry
found in cap29-acq1 (sto 0.045-0.085 vs det 0.32-0.38 progress_ratio).
`probe_turn_authority` (own cfg, wz_cmd=+-0.25, seeds 0/1) confirms
turn authority is UNAFFECTED by seed or dose on all 4 arms (wz_med
0.189-0.209/-0.198 to -0.213, all >> the 0.07 floor) — not the failure
mode either way. `purewalk` det/sto (dr-scale=0.2, matching the
lineage's own ancestor baseline `purewalk_gradclip0p15_acq1_cap29_det`:
det prog 0.35/slip 2.69): **`hi`/`hi-s1` (-3.5 dose) CANARY PASS-for-
acquisition** — sto prog 0.28-0.32 (78-100% of own det 0.31-0.36),
clearing the "~0.15+" bar with room, slip flat-to-better in sto, zero
falls 32/32. **`mild`/`mild-s1` (-2.0 dose) CANARY FAIL - MECHANISM**
— sto prog only 0.11-0.13 (31-36% of own det 0.35-0.37), missing the
0.15 bar; det slip also up 40-55% over baseline on both arms. Clean
2-seed-per-dose dose-response, not noise: -2.0 is the right direction
but under-shoots; -3.5 clears it. **Funded the acq-scale follow-up on
the winning dose only**: `...cap29-stdwalklohi-acq1{,-s1}`, full 38M
budget, same recipe as `cap29-acq1` (one lever changed), VERIFIED
RUNNING train-6/7. Gate: flat-only `eval_done_gate_session` n>=12
det+sto DR-0+own-DR vs the cap29-acq1 baseline (46.8 deg/3.09; acq1
itself came in worse at 55.5-61.1/3.45-3.46) — PASS if steering+slip
drop to/below baseline AND convergence survives at session scale;
PARTIAL if falls+convergence hold but steering doesn't (Next item 1);
FAIL if sto regresses at scale (credit-assignment angle next).
Evidence: `logs/ckpt_eval/{turn_probe,purewalk}_..._stdwalklo_
{mild,mild_s1,hi,hi_s1}*`.
