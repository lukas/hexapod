# standwalk STATUS journal archive — 2026-09-05e

Verbatim full text of the 09-05 ~06:1x Update block (group duty-cycle
skew build + zero-training refutation), trimmed to a short pointer in
the live STATUS.md for line-budget reasons.

---

Update, 2026-09-05 ~06:1x: **first genuine gait-STRUCTURE candidate
(group duty-cycle skew) built, tested, and REFUTED at zero training
cost — same cycle that closed the multi-teacher axis, no GPU spend.**
Built `TripodGait.combined_group_duty_skew` (`hexapod_core/tripod_
gait.py`): on a combined tick, `_classify_group_heavy` finds which
tripod-parity group (0={0,2,4}/1={1,3,5}) holds MORE "amplified" legs
(proven a static function of leg angle + command sign only, phase/
prog-independent — verified empirically across a full phase sweep and
all 4 vx/omega sign combos), then re-times ONE shared boundary on the
phase circle so that group's swing window widens (its own stance
narrows, the other group's window narrows/widens in exact complement)
— SAFE BY CONSTRUCTION (still always exactly one group swinging, the
other stancing, at any dose; no per-leg support-polygon risk, unlike
a genuine per-leg duty split). Bit-exact off at dose 0 and on any
pure-turn/pure-walk tick regardless of dose (7 new unit tests,
`test_tripod_gait_group_duty_skew.py`, all green; full sibling-test
+ probe_turn_authority bank re-run clean, 35/35). Wired a matching
`--scripted-group-duty-skew` flag into `probe_turn_authority.py` and
ran a zero-training scripted-teacher sweep (`vx=0.08`, `wz=+-0.25`,
skew in {+-0.15,+-0.3,+-0.44} vs the 0.0 baseline which reproduces the
pinned 0.0723/-0.0738 reference exactly): combined-tick wz_med gets
MONOTONICALLY WORSE with |skew| in BOTH directions (widen-the-heavy-
group: 0.0723->0.0721->0.0607->0.0284; widen-the-light-group instead:
0.0734->0.0599->0.0234) — a small, likely-noise +1.5% wobble at the
smallest negative dose, then collapse either way. **This refutes the
simplest (whole-group) duration lever exactly like every magnitude
lever before it** — breaking the gait's 50/50 temporal symmetry
degrades tracking faster than any targeted per-group relief helps,
in EITHER direction. Root-cause hypothesis (not yet verified): the
narrowed group's STANCE-phase commanded yaw rate rises just as much as
the widened group's swing-phase rate falls, since `safety.max_delta_
q_deg` clips the commanded yaw angle continuously through stance too
(the foot is still rotating relative to body while planted) — this
was flagged but NOT measured this cycle (would need `probe_joint_
tracking.py` extended with the new flag); left as a NEXT step only if
a future per-leg (not whole-group) variant looks promising enough to
justify the extra instrumentation. No RL canary launched (would be
premature given the zero-training result is already decisively
negative — an unsafe-BY-EFFORT half-built RL wire-up would have been
exactly the "half-build" the prior update warned against). Knob kept
in-tree (bit-exact-off), matching the codebase convention for every
other refuted-but-documented lever in this file. Evidence: `/tmp/
gds_scripted_{0.0,0.15,0.3,0.44}.json`, `/tmp/gds_scripted_neg_-{0.15,
0.3,0.44}.json`, `/tmp/gds_scripted_pureturn_check.json` (pure-turn
bit-exact re-confirmation at dose 0.3).
