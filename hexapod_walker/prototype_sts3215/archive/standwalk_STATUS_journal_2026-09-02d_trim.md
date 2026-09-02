# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-02 ~05:4x (idle-kick, drained Next item 2 — frame-blend
joint verdict, zero new training compute, pulled+read both pending
on-pod session files): **frame-blend is REFUTED, not just
"unconfirmed."** `frameblend-canary` (seed0) and `-s1` (seed1)
flat-only `eval_done_gate_session` (n=32 each) both landed: seed0
27/32 term vs its no-blend control's 24/32 (worse); seed1 21/32 term
vs its control's 5/32 (4x worse). Both directions agree: blending only
the obs-facing switch handoff does not touch the dominant mid-rise
sustained-femur-current fragility (see item 2 below), so total
terminations don't drop and in seed1's case explode. Verdicted
`CANARY FAIL - MECHANISM` on both runs; no further frame-blend dose
sweeping. Item 1 (cap=2.9 decisive session read) is still mid-flight
on train-1 (started 05:18, ETA ~1-2h, not yet read this cycle).

Interim check 09-02 ~07:3x (idle-kick, zero new compute, no verdict —
job still running): the flat-only dr0 HALF of the cap=2.9
`eval_done_gate_session` for `durctrl-canary` finished at 06:52 and is
already decisive on its own axis — **16/16 det+sto episodes
`seq_completed=true`, ZERO terminations**, femur `cur_max_a` still
2.64 (still riding the cap, not lowered) but no longer tripping it,
vs. the un-capped control's 24/32 session-level over_current rate.
own-DR half started 06:52, ~7/8 det episodes rendered by 07:35 (own-DR
sto not started yet) — ETA ~45-60 more min. Matches the cap-raise
prediction so far; still waiting on own-DR before landing the cfg
default per item 1's own criteria (do not act on the dr0-only half).

Prior update, 2026-09-02 ~05:3x (idle-kick): the SAME per-joint current
probe run against the LEGACY primitive-family (2.104kg)
`ppo_goal_cw_stance_dr10` found femur pins at the IDENTICAL ~2.64A cap
(8/8 episodes, 5/8 terminate) — **mass REFUTED** as the sustained-
current driver, it's intrinsic to the curl-up-from-flat rise motion at
both body weights. Cheap zero-training follow-up: raising
`safety.max_current_a` 2.5->2.9A (grounded in HARDWARE.md's recorded
real 2.97A/"3A lab guard") eliminated all terminations (0/8) on the
same read-only probe. Front-running lever is now **raise
`safety.max_current_a`**, gated on the in-flight `durctrl-canary`
`eval_done_gate_session` cap=2.9 read (item 1, train-1, still mid-
flight). Full detail archived verbatim in
`archive/standwalk_STATUS_journal_2026-09-02c_trim.md`.

## Next (meta 09-02 ~05:3x)

1. **TOP ITEM: read the in-flight cap=2.9 `eval_done_gate_session`

[archived verbatim by meta 09-02 ~09:1x before the cap=2.9 decisive
rewrite; the "## Next (meta 09-02 ~05:3x)" list it referenced is in
the STATUS git history at 7dc09287]
