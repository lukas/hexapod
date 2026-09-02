# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-02 ~10:4x: **cap29-acq1 pair TRAINING FINISHED** (38M
steps each, healthy reward curves, fps>11k) — Next item #1's read is
now IN FLIGHT: flat-only `eval_done_gate_session` (n=8/pass x4 passes
= 32 total, matching the durctrl-canary decisive-read precedent),
launched on-pod (acq1 on train-3, `-s1` on train-1), both registered
via `ops.sh evalpending`. Not yet read.

Prior update, 2026-09-02 ~09:3x (idle-kick executed item 1+2, zero
backlog left): **cap=2.9 LANDED as a training-time acquisition** —
`cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-acq1`
(seed0, train-3) + `-s1` (seed1, train-1), warm-started from the
lineage's own best walk-quality+turn-authority checkpoint (the 2M
`gradclip0p15-canary`, NOT the degraded 38M `-acq1` — that acq1 run
itself REGRESSED walk quality under the OLD 2.5A cap, see its own
PARTIAL verdict), `safety.max_current_a=2.9` set both training- and
eval-time.

Item 2 (read-only re-probe, zero training compute) **CLOSED this
cycle**: reran `probe_turn_authority` + a purewalk det harness on
`klrolltight-acq1` and `gradclip0p15-acq1` with
`safety.max_current_a=2.9`. **Turn ceiling is REAL, NOT
current-confounded**: both checkpoints' wz_med (klrolltight 0.081/
-0.110, gradclip0p15 0.188/-0.224) are unchanged from their archived
cap-2.5 reads within noise. **But walk QUALITY improves under the
raised cap** (side-finding): gradclip0p15-acq1 purewalk det prog 0.35/
slip 2.81/dir_err 46.4°/cur_max 2.58A/zero term vs its cap-2.5 PARTIAL
(prog 0.31-0.32/slip 4.9-5.8) — corroborates item 1's hypothesis that
the old cap's spurious terminations, not steering, capped walk
quality. klrolltight-acq1 purewalk det: gait_valid 8/8, zero term,
prog 0.36-0.39, slip 2.74-3.16, dir_err 43.4°. Evidence:
`logs/ckpt_eval/turn_probe_{klrolltight_acq1,
yawcredit_gradclip0p15_acq1}_cap29.json`,
`logs/ckpt_eval/purewalk_{klrolltight_acq1,gradclip0p15_acq1}_cap29_det.json/`.

## Next (idle-kick 09-02 ~09:3x)

1. **Read the cap29-acq1 pair's flat-only `eval_done_gate_session`**
   (launched 10:4x, IN FLIGHT on train-3/train-1, registered via
   `ops.sh evalpending`, ETA hours). Gate: zero falls (bar MET by the
   teacher control `durctrl-canary` at 32/32 — regression here
   refutes); direction_err_med/slip_per_m_med at/below the cap29
   zero-training baselines (46.8°/3.09) — the purewalk side-read above
   (dir 43-46°, slip 2.7-3.2) suggests this is plausible, not yet
   confirmed at full acquisition scale or on the session harness.
2. **Steering gap (direction_err ~44-47°, cap 2.5 or 2.9) is the
   largest remaining DONE-gate distance, CONFIRMED not a current
   artifact** (item 2, closed) — design the next arm against the
   literal 60s session direction-following read, not the short probe.
3. **Closed (see archives):** update-size constraints, reward pricing,
   exploration magnitude, anchor dose, turn-skip, yaw-credit clip
   doses, mixedsession-audit + diet scoping (x2), duration-mismatch,
   switch-jump lead, ramp/height/mass as current driver, frame-blend
   (n=2), cap-diagnostic (POSITIVE), current-confound re-probe
   (NEGATIVE — ceiling real).

(Continued trim, moved 2026-09-02 ~15:3x cycle, VERBATIM)

Prior update, 2026-09-02 ~10:4x: cap29-acq1 pair TRAINING FINISHED (38M
steps each, healthy reward curves, fps>11k) — Next item #1's read is
now IN FLIGHT: flat-only `eval_done_gate_session` (n=8/pass x4 passes
= 32 total, matching the durctrl-canary decisive-read precedent),
launched on-pod (acq1 on train-3, `-s1` on train-1), both registered
via `ops.sh evalpending`. Not yet read.

Prior update, 2026-09-02 ~09:3x (idle-kick executed item 1+2, zero
backlog left): **cap=2.9 LANDED as a training-time acquisition** —
`cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-acq1`
(seed0, train-3) + `-s1` (seed1, train-1), warm-started from the
lineage's own best walk-quality+turn-authority checkpoint (the 2M
`gradclip0p15-canary`, NOT the degraded 38M `-acq1` — that acq1 run
itself REGRESSED walk quality under the OLD 2.5A cap, see its own
PARTIAL verdict), `safety.max_current_a=2.9` set both training- and
eval-time.

Item 2 (read-only re-probe, zero training compute) **CLOSED this
cycle**: reran `probe_turn_authority` + a purewalk det harness on
`klrolltight-acq1` and `gradclip0p15-acq1` with
`safety.max_current_a=2.9`. **Turn ceiling is REAL, NOT
current-confounded**: both checkpoints' wz_med (klrolltight 0.081/
-0.110, gradclip0p15 0.188/-0.224) are unchanged from their archived
cap-2.5 reads within noise. **But walk QUALITY improves under the
raised cap** (side-finding): gradclip0p15-acq1 purewalk det prog 0.35/
slip 2.81/dir_err 46.4°/cur_max 2.58A/zero term vs its cap-2.5 PARTIAL
(prog 0.31-0.32/slip 4.9-5.8) — corroborates item 1's hypothesis that
the old cap's spurious terminations, not steering, capped walk
quality. klrolltight-acq1 purewalk det: gait_valid 8/8, zero term,
prog 0.36-0.39, slip 2.74-3.16, dir_err 43.4°. Evidence:
`logs/ckpt_eval/turn_probe_{klrolltight_acq1,
yawcredit_gradclip0p15_acq1}_cap29.json`,
`logs/ckpt_eval/purewalk_{klrolltight_acq1,gradclip0p15_acq1}_cap29_det.json/`.
