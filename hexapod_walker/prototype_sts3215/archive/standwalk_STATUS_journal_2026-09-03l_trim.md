Update, 2026-09-03 ~15:2x (idle-kick, tool-building on Next item 2
sub-step (i)): **built the missing tool the prior Update's "recommended
next step (i)" named** — `eval_checkpoint.py` had no way to dump a
real per-tick qpos/qvel/action/servo_current/height trace, only
aggregate metrics. Added `run_episode(..., trace_sink=list|None)`
(default `None`, byte-identical return value — proven by test) +
`--rollout-trace-out/-mode/-tag/-index` CLI flags + `_save_rollout_trace`
(.npz writer, embeds the episode's own summary dict for provenance).
4/4 new tests green (`test_eval_checkpoint_rollout_trace.py`); reran
the seed1 isolated-rise DR-0 det panel (n=8, own cap 2.5, matching the
14:2x dig-in's own protocol) and captured TWO real traces:
`logs/ckpt_eval/yawdensity_s1_riseAB_cap29cf/rollout_trace_det{0,5}_
{overcurrent,silentstall}.npz`. First read confirms the video-based
"isometric fight" call QUANTITATIVELY: the silent-stall episode's
height plateaus at 29mm (target 86.5mm) from t~6s onward for the
remaining 24s while its hottest servo (idx 4) sits >2.0A for 82.6% of
the episode — a real, sustained isometric stall, not a transient
current spike. The over_current episode shows the opposite shape: 3
servos hit the 2.64A ceiling within 0.4s (fast trip, not a slow climb).
Both are now real qpos/action replay material for rebuilding the
rise-stall semantics-bank twin as a faithful replay instead of a
hand-built guess (Next item 2 sub-step (i), still open — the replay
twin itself is not built yet, only its input data now exists).
Snapshot `e579a144` (`exp/standwalk-riseB-rollout-trace-tool-09-03`).

Earlier updates (15:0x semantics-bank twins, 14:2x seed1 dig-in
resolution, 13:3x seed0 verdict, 13:2x initial flagged dig-in, and
everything before) moved VERBATIM to `archive/standwalk_STATUS_
journal_2026-09-03k_trim.md` + `2026-09-03{a..j}_trim.md` +
`2026-09-02{f,h}_trim.md`. (NOTE added by the 09-03 ~16:0x cycle: the
09-03{a..k}/09-02{f,h} archive files referenced above do not actually
exist on disk under those names — likely a stale/never-materialized
compaction claim from an earlier cycle. Not reconstructed here (no
recovered source content); flagging so a future compaction pass knows
the chain has a gap rather than assuming it is intact.)
