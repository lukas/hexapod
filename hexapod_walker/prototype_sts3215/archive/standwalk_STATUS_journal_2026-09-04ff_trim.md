# standwalk STATUS journal archive — 2026-09-04ff (verbatim trim)

Archived from `rl_docs/tracks/standwalk/STATUS.md` before the
mlcontprice8-verdict banner rewrite (2026-09-04 ~13:2x). Superseded by
the new Update banner; do not act on the Next items below, they are
history.

Update, 2026-09-04 ~11:4x: `transtress-s1-acq8m` (8M continuation of the
clean seed1 canary) TRIAGED — FAIL vs its own pre-registered gate, and
it REFRAMES Next item 1's "seed-dependent divergence" as a budget/
timing effect, not a true fork. eval_cmd_stress at 8060928 steps:
hold_min_load reappeared (6/72, all mid-transition-hold segments, the
documented segment-entry-EMA-reset mechanism) and gait_valid_frac
dropped to 0.986 with sacrificed_legs_seen=[1,2,3] — the SAME
sacrificed-leg signature seed0's `transtress` showed AT 2M (legs
[3,4,5]). Walk quality itself did NOT regress (progress_ratio/dir_err
both improved vs the 2M read; smoothness tied). Reward rose the whole
8M window (08-21 ruling: not a collapse) but the run's own FAIL clause
named the fix in advance: a priced/carried-over segment-switch
foot-load mechanism, not more steps — "more budget" is now measured to
NOT close this alone. Verdict: `transtress-s1-acq8m`. Prior 08-3x
banner (over_current audit, `eval_cmd_stress.py` suite,
`goal.mode_seq_stress` default-OFF, snapshot 2751a537) archived:
`archive/standwalk_STATUS_journal_2026-09-04ee_trim.md`.

## Next (updated 09-04 ~11:4x)

1. **Universal-command branch — root cause is now MECHANISM-LEVEL, not
   seed-level; fix the segment-switch foot-load gap before any further
   acquisition rung on this diet.** `eval_cmd_stress` (seed 93000, 72
   seq eps, dr0+ownDR): `transtress-s1` PASS clean at 2M — ZERO mech
   terms (control `cont-s1`: 38/72=52.8%!), completion 1.0 (vs 0.472).
   Seed0 `transtress` FAILS the SAME eval at 2M vs its own control
   `cont`: 33/72 mech terms, 3 sacrificed legs [3,4,5]. `transtress-s1`
   continued to 8M (`-acq8m`, FAIL verdict 09-04 ~11:4x): the clean win
   partly erodes with budget too — 6/72 hold_min_load (all
   walk->lower->rise / walk->hold / rise->hold mid-transition entries,
   the documented per-foot EMA-has-no-carry-over-across-a-switch bug,
   `sim_env.py`/`manual_drive_session.py`) and sacrificed_legs_seen
   [1,2,3] reappears — matching seed0's early pathology, just later/
   milder (8.3% vs seed0's ~46% at 2M). Both seeds drift the SAME
   direction; this is a shared mechanism gap, not a seed coin-flip.
   FIX LANDED (09-04 ~12:xx, this cycle, dig-in of the acq8m FAIL):
   measured first that with grace 1.0 s = 4x tau the stale/zero entry
   EMA washes out (e^-4) before the termination clock unpins — the
   entry artifact alone cannot fire the cliff; the fires are a REAL
   unloaded-through-the-switch foot whose only training signal was the
   cliff ~2 s after the causal placement. Landed BOTH halves,
   default-off/bit-exact (sim_env.py): `safety.hold_min_load_ema_
   continuous=1` (EMA seeded from measured load at reset + updated
   every tick in every mode — hold entries read the load actually
   carried through the switch) and `reward.k_hold_min_load_short`
   (dense hold-tick price `-k*dt*max(0,1-ema/floor)`, same EMA/floor
   as the termination, active through the grace window — the priced
   twin per the 08-24 ruling). Semantics bank: 6 new tests green
   (test_hold_minload_cont_*/short_* in test_task_semantics.py) +
   existing minload/grace banks green. CANARY PAIR LAUNCHED: 2M
   mechanism-health arms `...-acq8m-mlcontprice2/-mlcontprice8`
   (k=2.0/8.0, continuity on, continuing the acq8m checkpoint on the
   same stress diet — repair test; acq8m is otherwise the lineage's
   best walker). Gate: eval_cmd_stress seed 93000, zero hold_min_load
   + gait_valid 1.0 + walk within 10% of the acq8m read. Seed0
   `transtress`'s own video/per-leg dig-in stays lower-priority (same
   mechanism, already characterized). Numbers: `cont`/`cont-s1`/
   `transtress-s1`/`transtress-s1-acq8m` verdicts (09-04).
2. **Steering branch — CONFIRMED continuation-drift confound; axis
   needs re-scoring, not more lever canaries.** `cont`/`cont-s1`
   `probe_turn_authority` pure-turn wz_med sits 22-35% below the FROZEN
   cap29-stdwalklo-hi{,-s1} baselines gating all ~26 steering-lever
   canaries (6 families) — from PLAIN continuation, zero lever.
   Re-scored vs this matched control, `selomegaboost4p0-s1` (verdict
   pending its podeval DR-0 proxy, running on train-2) looks BETTER on
   pure-turn (+30-46% vs `cont-s1`) and mixed on combined-tick (neg-wz
   better, pos-wz ~8-17% worse) — opposite of scoring vs the frozen
   baseline (flat/failing like every prior lever). DIG-IN owed:
   re-score the 6-lever-family FAIL wall vs matched continuations
   before declaring the axis closed, or at minimum re-open
   `selomegaboost4p0-s1` once its DR-0 proxy lands. Numbers: `cont`/
   `cont-s1` verdicts + `logs/ckpt_eval/probe_turn_authority_
   cap29_stdwalklohi_{cont,cont_s1,selomegaboost4p0_s1}_combined_
   09-04.json`. Rise-stall stays CLOSED (09-03o archive).
3. **Closed** (full list in archives 09-02{,b..h}, 09-03{a..u},
   09-04{aa,cc,dd}): architecture-split; lever/dose/seed sweeps up to
   09-04 (all FAIL/REFUTED pre-continuation-drift-finding, see item 2);
   cap29 acquisition (PARTIAL); log_std anneal grid; sto/det
   convergence; resamplematch; rise over_current dig-in; semantics-bank
   twins; IK-feasibility groundwork.
