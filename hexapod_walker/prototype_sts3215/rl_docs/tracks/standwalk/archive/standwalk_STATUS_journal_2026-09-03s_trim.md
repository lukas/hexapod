Update, 2026-09-03 ~23:0x (**Candidate (i)-v2 built + zero-training
gate PASSED: a NEW `TripodGait.combined_yaw_arm_scale` lever shrinks
the combined-tick yaw clip without touching pure-turn at all — 4-cell
RL canary LAUNCHED to test survival through fine-tune.**)

Two same-mechanism variants closed first, zero-training: (1)
discounting omega on combined ticks (mirror of the already-refuted
`bc_anchor_teacher_omega_boost`, dose<1) does NOT help even at the
scripted level — combined `wz_med` gets MONOTONICALLY WORSE as the
discount strengthens (1.0->0.3: 0.0723->0.0620 rad/s), because the raw
per-tick yaw delta is a period-INDEPENDENT direct function of physical
foot velocity — any uniform demand scaling (either sign) trades
achieved rotation 1:1 against clip relief; this closes the WHOLE
omega-scaling axis (boost refuted 4/4 at the RL stage 09-03 17:5x,
discount now refuted zero-training). (2) The literal candidate (b)
text ("pre-slew the target to the same cap") is mathematically a
NO-OP: the raw signal is already a constant-slope triangle wave, so a
same-cap rate limiter already achieves the max amplitude — no
"reversal waste" to recover upstream.

**The new lever**: `TripodGait.desired_deg()` gained
`combined_yaw_arm_scale` (default 1.0 bit-exact) which inflates ONLY
the `atan2` denominator used to back out the yaw SERVO ANGLE from a
leg's true tangential foot swing — hip/knee IK still use the TRUE
`r_planar`/z target, so placement/lift are untouched; only the
commanded yaw excursion shrinks. Gated to combined ticks only (mirrors
the omega-boost gate) so pure-turn is bit-exact (8/8 seeds/signs
verified). Zero-training gate (dose 1.0->2.0): `probe_turn_authority
--scripted-yaw-arm-scale` combined `wz_med` improves 0.0723->0.0807
(+11.6%) / -0.0738->-0.0791 (+7.2%) at flat `vx_med`, pure-turn stays
EXACTLY 0.2198 every dose; `probe_joint_tracking` confirms the
mechanism — combined `clip_sat_frac_yaw` drops 0.477->0.226 (pure-turn
untouched). Past dose ~2.5 the gain reverses (non-monotonic, real).
Wired via `train.bc_anchor_teacher_yaw_arm_scale`; 7 new tests +
3 probe tests green; full `test_bc_anchor.py` (105/105) rerun, same
PRE-EXISTING unrelated failures as unmodified `main` in two other
semantics files (confirmed via `git stash` A/B), no new breakage.
Snapshot `cce362ba` (`exp/standwalk-yaw-arm-scale-lever-09-03`).

**LAUNCHED**: 2-dose (1.5, 2.0) x 2-seed canary respec'd from the
matched comparators `cap29-stdwalklo-hi{,-s1}` (+ rider (a)
`safety.max_current_a=2.5`): `cap29-stdwalklohi-yawarm{1p5,2p0}{,-s1}`,
all 4 VERIFIED RUNNING (train-1/2/4/5). NEXT CYCLE: read with
`probe_turn_authority --vx-cmds` vs the pre-registered gate (beat
`cap29-stdwalklo-hi{,-s1}`'s own combined read +0.110/-0.171 on BOTH
signs, <=10% pure-turn/straight-walk regression) — read the FULL
reward curve first (rider c: every cap29 sibling so far showed a Q3
dip/recovery shape that is not itself a fail signal). Prior banner
moved VERBATIM to `archive/standwalk_STATUS_journal_2026-09-03r_trim.md`.
