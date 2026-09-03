# standwalk STATUS journal archive — 2026-09-03q (VERBATIM)

Prior "Update" banner text, superseded by the 09-03 ~22:xx banner
(joint-tracking instrument built, candidate (i) hypothesis (a)
confirmed on the scripted teacher). Moved here verbatim, unedited.

Update, 2026-09-03 ~21:1x (**Candidate (ii) (`reward.walk_yaw_
combined_boost`) CLOSED: 4/4 canary cells FAIL — pure-turn regression
blows the 10% cap every time, even where the combined-tick number
itself beats the comparator.**)

Read the full 4-cell batch (`cap29-stdwalklohi-yawboost{3p0,6p0}
{,-s1}`) with `probe_turn_authority.py --vx-cmds` (full training
cfg-set replayed per checkpoint for an exact obs-contract match) vs
each cell's seed-matched control (`cap29-stdwalklo-hi{,-s1}`).
Pure-turn regression vs control / combined-vs-comparator(+0.110/
-0.171): 3p0(s0) 46.9%/17.8% regression, + WORSE than control (0.063),
- beats; 3p0-s1 18.2%/28.1%, + fails (0.101), - beats; 6p0(s0)
26.8%/10.8%, + fails (0.101), - fails too (0.133); 6p0-s1 15.3%/31.2%,
+ beats (0.120), - beats (0.188). Every cell blows the pre-registered
<=10% pure-turn regression cap (the gate's own disqualifying clause),
most by 2-4x; only one of four (6p0-s1) even clears the combined-tick
comparator on both signs, and it still fails the regression cap. No
falls in any probe rollout (32/32 `fell=False`); training reward shows
the same rider-(c) Q3 dip/recovery shape as every cap29 sibling — a
mechanism trade-off, not a training-collapse story. **Candidate (ii)
REFUTED at every dose (3.0/6.0) and seed (0/1)**: boosting the
yaw-kernel income on combined ticks reallocates supervision away from
pure-turn ticks through the shared GRU/value-function update — correct
in its FIRING gate, not clean in its EFFECT. Verdicts + evidence on
ledger/W&B (`logs/ckpt_eval/probe_turn_authority_yawboost{3p0,3p0_s1,
6p0,6p0_s1}_combined_09-03.json`). Earlier build/launch note moved
VERBATIM to `archive/standwalk_STATUS_journal_2026-09-03p_trim.md`.

**Candidate (i) groundwork (not a validated harness yet — Next item
2):** per this item's fallback, started the zero-training diagnosis a
`tripod_gait.py` geometry edit needs before any GPU spend. (1) IK
feasibility is NOT the bottleneck: walking the scripted teacher's own
`_foot_target_in_body -> _leg_ik` chain at the combined command
(vx=0.08, wz=+-0.25) over a full 15s episode, `_leg_ik` never returns
`None` and the tightest workspace margin is 47mm — always reachable.
(2) The `safety.max_delta_q_deg=0.375` slew cap is already deeply
saturated in BOTH regimes (raw per-tick joint delta median: pure-turn
0.93deg/tick, 82% over cap; combined 0.99deg/tick, 99.6% over cap) —
both ~2.5x over the cap already, which is odd given achieved body wz
is ~3x higher for pure-turn (0.22-0.25) than combined (0.07-0.19): if
slew-clipping alone drove the gap, both should saturate similarly.
This points AWAY from "the vx+omega superposition formula is simply
wrong" and toward the loss living downstream — either the SafetyLayer
clip interacting differently with a two-term (translate+rotate) vs
one-term (rotate-only) raw target, or genuine stance-leg contact/slip
physics competing for a shared thrust budget. Neither sub-hypothesis
is measured yet; DIG-IN flagged for the live-sim desired-vs-actual
joint-tracking instrument this needs (see Next item 2).
