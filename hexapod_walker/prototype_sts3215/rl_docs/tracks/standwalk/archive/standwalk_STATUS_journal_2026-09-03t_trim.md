Update, 2026-09-03 ~23:1x (**Candidate (i)-v2 seed0/dose1.5 read:
CANARY FAIL — combined-tick wins BOTH signs cleanly for the first time
via a pure geometry lever, but pure-turn regression still blows the
10% cap. Also found + fixed a probe-usage gotcha: the abbreviated
5-flag cfg shorthand used in prior verdict prose silently FREEZES the
policy (near-zero wz on a known-good checkpoint) — the full non-train
cfg-set must be replayed.**)

`cap29-stdwalklohi-yawarm1p5` (seed0, dose 1.5) verdicted FAIL-
MECHANISM. `probe_turn_authority.py --vx-cmds` (full 84-key non-train
cfg-set replayed — see gotcha below): pure-turn `wz_med` (seed-avg)
+0.196/-0.187 vs control `cap29-stdwalklo-hi` +0.221/-0.250 →
regression 11.7% (+) / 25.4% (-), BOTH over the 10% cap. Combined-tick
(`vx=0.08`) `wz_med` +0.143/-0.219 vs the pre-registered comparator
+0.110/-0.171 → BOTH signs beat it cleanly (+30%/+28% magnitude) — only
the second mechanism ever to do this (after `yawboost6p0-s1`; every
`combskip`/`omegaboost` cell was sign-asymmetric). No falls (8/8 probe
rows). Reward: quarters `[24.2, 74.9, -191.1, 137.2]`, final `ep_rew_
mean` 238.4 — same rider-c Q3 dip/recovery shape as every cap29
sibling, actually the family's best final value so far. Per the
pre-registered gate (needs both signs to beat the comparator AND
<=10% pure-turn regression), this FAILS on the regression clause alone
despite the genuine combined win — reinforcing a real pattern: 2/2
mechanisms that win the combined axis on both signs at once still cost
pure-turn beyond cap. `dose 2.0` (same seed) is still training; the
1.5-seed1 twin belongs to a concurrent cycle. Full verdict + evidence:
`rl_docs/runs/cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-
gradclip0p15-cap29-stdwalklohi-yawarm1p5.md`.

**PROBE-USAGE GOTCHA (logged, not yet a code fix):** `probe_turn_
authority.py --vx-cmds` requires the FULL non-`train.*` cfg-set from
the checkpoint's training command, not the 5-flag shorthand
(`goal.walk_yaw_cmd`, `obs.mode_onehot`, `goal.mode_seq`, `goal.walk_
phase_obs`, `goal.walk_obs_body_vel`) quoted in several prior verdict
paragraphs as "the cfg to match training obs width". Re-running the
KNOWN-PASSING control `cap29-stdwalklo-hi` with only those 5 flags
reproduces a near-zero/frozen `wz_med` (~0.002) even though the
checkpoint truly tracks turns fine (+0.221/-0.250 once the full cfg is
replayed) — almost certainly a missing `goal.walk_phase_hz`/`goal.walk_
phase_run_on_yaw` (or another goal.* field feeding the phase-obs
channel) putting the model on a badly out-of-distribution observation,
not a genuine behavior. `n_walk_ticks`/mode composition matched exactly
between the short and full cfg (mode sequencing is a DR-free function
of seed, independent of the policy), which is why this was not obvious
from tick counts alone — always diff wz_med against a fresh control
re-run with the SAME cfg-set before trusting a probe read, and default
to replaying the full training cfg-set for any future combined-tick
probe run. Every PRIOR combined-tick verdict in this branch (combskip,
omegaboost, yawboost, this run) that explicitly said "full training
cfg-set replayed" is unaffected; only the shorthand-cfg summaries in
verdict prose were ever at risk, and none of those summaries were
themselves used to compute the numbers quoted (spot-checked: the
quoted numbers match a full-cfg recompute for `omegaboost1p5` control
figures already in evidence).

**NEXT CYCLE:** read dose-2.0 (still training) and the 1.5-seed1 twin
once available; if both also show the same shape (real combined win,
disqualifying pure-turn cost), candidate (i)/(i)-v2 and the whole
omega-scaling axis close together, and item 2 should escalate to a
structurally different lever (phase-scheduled BC-anchor strength, per
the redesign spec's next class) rather than another single-scalar
dose on the same trade-off. Prior banner moved VERBATIM to
`archive/standwalk_STATUS_journal_2026-09-03s_trim.md`.
