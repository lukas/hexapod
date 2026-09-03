# standwalk STATUS journal archive — 2026-09-03m

Verbatim archive of the two "Update" blocks that were at the top of
`rl_docs/tracks/standwalk/STATUS.md` before the 09-03 ~17:2x combskip
verdict update replaced them. Moved to stay under the STATUS.md line
budget. Do not act on this as current state — read STATUS.md's
current top Update instead.

---

Update, 2026-09-03 ~16:4x (idle-kick, Next item 2, branch (b) —
**LEVER BUILT + IN FLIGHT**): implemented the combined-tick BC-anchor
gate named as the untried next action: `train.bc_anchor_walk_combined_skip`
(env-side, `sim_env.py`, default 0 = off, bit-exact — mirrors the
already-existing pure-turn `bc_anchor_walk_turn_skip`), zeroing the
walk BC-anchor's emitted target on COMBINED ticks (`vx_ref!=0 AND
wz_ref!=0`) only, leaving pure-turn and straight-walk ticks untouched.
5 new tests green in `test_bc_anchor.py`
(`test_walk_combined_skip_*`, incl. a compose-with-turn-skip test
proving the two gates never double-fire on the same tick) — this is
the mechanism's alignment proof (mirrors the bar the pure-turn
version cleared before its own canary). Launched the matched pair
`cw-standwalk-...-cap29-stdwalklohi-combskip{,-s1}` (2M-step canaries,
seeds 0/1, otherwise byte-identical to the already-PASSED
`cap29-stdwalklo-hi{,-s1}` log-std-anneal-hi recipe — those two runs
ARE the matched controls, no duplicate control spend needed) — both
RUNNING as of this update. Pre-registered gate: probe_turn_authority
combined-tick wz_med must beat this cycle's own checkpoint-scope
combined read (yawdensity_canary_s1: +0.145/-0.107, 74%/54% of
pure-turn retained) without a >10% pure-turn/straight-walk regression
or new terminations vs the matched control. Snapshot `48ab3945`
(`exp/standwalk-bc-anchor-combined-skip-09-03`). Branch (a) (the
`tripod_gait.py` foot-target geometry fix) is NOT started — it is
shared hardware-adjacent code needing its own dedicated before/after
validation pass, correctly deferred rather than rushed this cycle.

Earlier update, 2026-09-03 ~16:0x (idle-kick, Next item 2 sub-step (ii) —
the OTHER named branch, "zero-training ablation scoped to COMBINED
walk+turn ticks"): **found a genuine, quantified, reproducible NEW
mechanism candidate: the scripted TripodGait reference itself — the
BC anchor's own imitation target, and the thing every prior
turn-authority probe held vx_ref=0 while testing — loses turning
authority in smooth proportion to how much forward speed is
simultaneously commanded.** Extended `probe_turn_authority.py` with a
`--vx-cmds` sweep (new kwarg `vx_cmd`, default 0.0 = bit-exact prior
behavior — proven by a new pinned-equality test; body-frame vx read
via the existing `env._body_vel_xy()[0]`, robust to a rotating
heading), 4 new tests green
(`test_probe_turn_authority.py`). Three zero-training (no PPO)
readings, none touching a GPU:
1. **Scripted teacher, dose curve** (vx 0/0.02/0.04/0.06/0.08 m/s at
   fixed wz_cmd=0.25): achieved wz falls MONOTONICALLY and smoothly —
   0.220 -> 0.182 -> 0.138 -> 0.084 -> 0.072 rad/s — a graded
   trade-off, not a step/threshold clip (rules out a discrete IK/
   workspace-limit artifact in favor of a shared thrust/turn-authority
   budget under the tripod gait's own foot-contact physics).
2. **Scripted teacher, matched grid** (pure-turn vs pure-walk vs
   combined, wz=+-0.25, vx=0.08): pure-turn wz_med +-0.220 (healthy);
   combined wz_med crashes to +-0.072/-0.074 — the teacher itself
   RETAINS ONLY ~33% of its pure-turn authority once walking forward.
3. **Same grid on the actual trained checkpoint**
   (`..._yawdensity_canary_s1.zip`, own cfg): pure-turn wz_med
   +-0.197/-0.199 (matches the STATUS's known-good "wz~0.18-0.23"
   read); combined wz_med +0.145/-0.107 — RL narrows the teacher's
   deficit (74%/54% retained vs the teacher's 33%) but does not close
   it, and vx also degrades combined (pure-walk vx_med 0.033 ->
   combined 0.015-0.023). This is the first direct evidence that part
   of the "course-holding during forward+turn mixes" gap is INHERITED
   from the open-loop reference the BC anchor imitates, not purely an
   RL/anchor-training-dynamics artifact — a genuinely different class
   from every anchor-coefficient/diet/structural lever already refuted
   (all of those tested PURE turn-in-place ticks only). Evidence:
   `logs/ckpt_eval/probe_turn_authority_combined_scripted_09-03.json`,
   `..._combined_scripted_dosecurve_09-03.json`,
   `..._yawdensity_s1_combined_09-03.json`. Did NOT touch
   `hexapod_core/tripod_gait.py` (shared hardware-adjacent production
   code) this cycle — a geometry change there needs its own dedicated
   validation pass, not a same-cycle patch. No GPU launch: the two
   live redesign candidates this unlocks (fix the teacher's combined-
   command foot-target geometry, or add a combined-tick-targeted
   course/yaw reward gate) each still need their own semantics-bank
   proof or hardware-adjacent-code validation before spending budget —
   see Next item 2 below. Snapshot `bd148144`
   (`exp/standwalk-combined-turn-probe-09-03`).

(Both of the above are now resolved: branch (b), built here, was
canaried and CANARY FAIL - MECHANISM verdicted 09-03 ~17:2x; see the
current STATUS.md top Update and the ledger verdicts for
`cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-combskip{,-s1}`.)
