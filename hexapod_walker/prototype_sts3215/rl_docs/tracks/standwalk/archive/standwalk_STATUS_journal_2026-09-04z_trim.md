# standwalk STATUS journal archive — 2026-09-04z (VERBATIM banner replaced by the 09-04 per-leg-instrumentation-and-two-refutations update)

Update, 2026-09-04 ~05:2x (**Confound-isolation pair READ — the
architecture-split axis is now DEFINITIVELY CLOSED, not provisional.
`TripleGruActorCriticPolicy` is dead; the sole live steering lever is
the teacher-side branch.**)

`cap29-stdwalklohi-dualcontinue-noyawcredit{,-s1}` (same start
checkpoint/steps/reward/goal/obs cfg-set and same dropped
`train.yaw_credit_coef/_vf_coef/_grad_clip` +
`--gru-dual-log-std-split`/`--log-std-anneal-core` mechanisms as the
Triple canary, but plain `--gru-dual`) finished and was read with the
same `probe_turn_authority.py --vx-cmds` (85-key non-train cfg-set
replay) instrument against the same `cap29-stdwalklo-hi{,-s1}`
control. Both pre-registered readings landed, and they agree:

- **Reading (A) CONFIRMED — the pure-turn loss is the mechanism drop,
  not the architecture.** This Dual-continuation regresses pure-turn
  `wz_med` 11.8-26.5% both signs, both seeds — matching the
  already-closed Triple canary's own 12.7-27.7% loss on the SAME
  confound-matched cells almost exactly. Dropping yaw_credit/
  log_std_split during ANY further continuation costs ~12-27% pure-
  turn authority by itself; those mechanisms are load-bearing, the
  architecture swap is not implicated by the pure-turn axis at all.
- **Reading (C) CONFIRMED — architecture bought nothing on
  combined-tick either, even with the identical confound in both
  arms.** This Dual run's own combined-tick (`vx_cmd=0.08`) `wz_med`
  beats or matches Triple's on all 8 matched cells (both signs, both
  seeds) — 2 cells even beat the ORIGINAL FROZEN control outright.
  Triple never wins a single combined-tick cell against a plain
  continuation sharing its own confound.
- Reading (B) (mechanisms innocent, pure-turn holds inside the 10%
  cap) did NOT land — ruled out by (A).

**Net: the architecture-split (`TripleGruActorCriticPolicy`) lever is
CLOSED for good — 2/2 Triple canary FAIL, confound now explained
rather than provisional, and even a maximally-favorable matched
comparison shows zero-to-negative combined-tick benefit.** Do not
build the `yaw_critic.py`-on-Triple follow-up, and do not spend a
"mechanisms-kept" clean Triple rerun either — (C) already answers the
practical question (architecture vs. plain continuation) on its own
terms, independent of how (A) vs (B) landed; a cleaner rerun would
only add methodological polish to an already-decided comparison. The
dualcontinue runs themselves are disqualified from adoption by their
own pure-turn regression (>10% cap) — they are explanatory controls,
not new candidates. Full per-cell numbers: ledger / W&B notes for
`...-dualcontinue-noyawcredit{,-s1}`.

**Steering branch state after this closure:** every policy-side lever
tried so far is now refuted (BC-anchor dose/skip x2 seeds, teacher
omega-boost x2 doses x2 seeds, combined_yaw_arm_scale x2 doses x2
seeds, walk_yaw_combined_boost x2 doses x2 seeds, TripleGruActorCriticPolicy
x2 seeds, and now the mechanism-drop confound explaining Triple's own
pure-turn loss). The ONE standing, independently-verified finding that
hasn't been chased yet is teacher-side: the scripted `TripodGait`
itself only retains ~33% of its pure-turn `wz` once walking forward
combined (09-03 16:1x). That is now the sole active lever — see Next.

Prior banner (`TripleGruActorCriticPolicy` build + 2/2 FAIL + the
confound discovery) moved VERBATIM to `archive/standwalk_STATUS_
journal_2026-09-04y_trim.md`.

**Same-cycle teacher-side groundwork (zero-training):** a
`probe_turn_authority.py --policy scripted` sweep of `wz_cmd`
0.05-0.25 at `vx_cmd=0.08` finds the scripted teacher's OWN
combined-tick `wz_med` nearly FLAT (0.056-0.073 rad/s) across the
whole range — a real ceiling, not proportional to the command past a
low threshold. Re-running with `safety.max_delta_q_deg` raised
0.375->8.0 (diagnostic only — it's a hard physical servo-bus contract,
never a production value) barely moves it (`wz_cmd=0.60` still only
reaches 0.16), so the bottleneck is `TripodGait`'s own combined
foot-target formula/thrust allocation, NOT the slew clip — consistent
with, and now quantified beyond, the 09-03 17:5x finding that vx
dominates the per-leg omega term. (Small-wz 0.05-0.10 pure-turn cells
in the same sweep read as unreliable measurement-window artifacts,
not capacity results — don't reuse them.) Next concrete step:
instrument per-leg foot-target magnitude across the vx sweep to see
exactly how omega gets starved, design one falsifiable formula fix,
and validate it zero-training with this probe BEFORE any RL spend.
