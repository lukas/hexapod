# META 2026-09-08 (nightly meta-analysis)

## 1. Progress toward the goal (last ~24h)
- **walkcurr (operator-designated primary, 09-05 order): REAL MOVEMENT.**
  Cartesian foot-target action space built, banked, and settled in one day:
  fork(a) warm-retrofit CLOSED (slip 2-6x control, cont20m ACQ FAIL);
  fork(b) fresh-init PARITY replicated n=3 seeds ON/OFF (0.86-1.02x, 0
  falls x6 arms) + durability 2/3 clean HOLDS at 50M (seed7 INCONCLUSIVE
  per corrected root audit). Crutch-removal map extended: halfgrav cell
  ignites; torque1x retention asymmetry closed (fb_20260908T090149);
  widen8 composite fresh-init FAILS n=2 in BOTH action spaces ->
  torqueretain bisection pair running now. First consistent structural
  slip lever found (env.foot_geom_radius_m, 15-26% zero-shot), first
  canary INVALID_PHYSICS (size-only compile bug, repaired d54506ef, root
  owns rerun). Ladder aim (widen8 ignition + slip floor) = the track's
  two real gaps. Correctly aimed.
- **todaypolicy: one real lead, queue was stale.** yawref candidate PASSES
  the full composed stand->joystick->lower A/B vs fresh incumbent
  (translation); arc undertracking localized to the slew-clip rate
  contract; 4 frozen causal screens (twistfit, eventsync, actionbank,
  coordinated) = 3 NULL + 1 one-sided authority. The measured next
  mechanism (turn/walk time-multiplexing) was saved-not-queued — FIXED
  tonight (Next refreshed, net 0 lines).
- **joystick: STALE 2 weeks, gate unmet, zero spend.** Filed
  q_20260908T0940Z (pursue via yawref/rung-0 lineage vs own frontier vs
  re-register). amp/cpg: DONE/closed, zero spend — correct.
  standwalk/assistfade: parked on "needs new mechanism design"; design is
  agent-doable but walkcurr holds the hardware order — acceptable, noted.
- **Consumed without moving much:** parity/durability replication depth
  (n=3 seeds x ON/OFF x 2 depths ~14 runs for a NULL result); triage-cycle
  dollars exceeded GPU cost. n=2 suffices for canary-level nulls.

## 2/3. Bottlenecks measured (cycles.json + .jsonl, 24h)

- 85 cycles, $442.87. sonnet $231/57 (avg $4.06), fable $212/19 (avg
  $11.14). By trigger: operator-kick $201/17 (45%!), refill $119/27,
  run-finished $101/25, evalready $15/6. Median 14.6 min, 73 turns;
  max $49.69/127 min (operator-kick cartfoot build — productive).
- **#1 sink: hand-rolled parses.** Sampled triage cycle: 68 bash calls,
  8+ `python3 -c` json/csv parses for reward-quarter reads the prompt
  bans hand-rolling. FIXED: `ops.sh quarters <run> [key...]` (cached
  wandb_history.csv, arbitrary keys) reproduces today's hand reads exactly.
- **#2 sink: walkcurr STATUS.md at 11,022 lines** — read/grepped by every
  walkcurr cycle (57 sonnet cycles today were walkcurr-dominated). FIXED:
  trimmed to 1,895 (-9,127), 09-07-and-older journal archived VERBATIM to
  archive/walkcurr_STATUS_journal_2026-09-07_trim.md (standwalk-established
  convention). Remaining big docs: amp 4,065 (inactive), joystick 2,573
  (inactive), assistfade 2,133, CURRENT_TRUTHS 1,747 (see below).
- **#3: verdict races** — >=5 scooped assignments (06:1x-09:1x); spawn
  dedupe + review ALREADY-VERDICTED banner (prior metas) cap each at a
  short cycle, but agents still re-verify scooped verdicts by hand
  (09:1x recomputed 4 arms to "concur"). Residual ~$15-25/day; judgment
  habit, not tooling — no prompt bloat added.
- **#4: RL_LOG verdict lines truncated mid-word** (head -c 220; 08:28
  line lost its conclusion). FIXED: 360-char cut + explicit
  "...(full verdict in ledger)" marker.

## Changes MADE (files, line deltas, rationale)

- rl_docs/tracks/walkcurr/STATUS.md: 11,022 -> 1,895 (-9,127); archive
  file +9,134 (verbatim). Cuts the primary track's per-cycle read cost.
- rl_move/orchestrator/ops.sh: +46 net (`quarters` helper; truncation fix;
  help line). bash -n green; live-tested on s41 cached history + edge cases.
- rl_docs/tracks/todaypolicy/STATUS.md: 1,515 -> 1,515 (net 0). Stale
  "nothing queued" replaced with the measured time-multiplex lead.
- OPERATOR_QUESTIONS.md +17 (joystick q). No watcher change/restart; no launches.

## Recommended, NOT made

- CURRENT_TRUTHS.md (1,747 lines): needs judgment-curation by a day cycle
  that knows which truths are load-bearing; mechanical night trim too risky.
- Null-result replication depth: default n=2 for canary-level parity/null
  reads — judgment note only, no new rule added (anti-bloat).
- fable operator-kick ROI ($201/day, 3/4 screens NULL): operator's call —
  the screens were operator-directed and cleanly pre-registered.

## Open questions for the operator

- q_20260908T0940Z: joystick track disposition (stale 2 weeks, gate unmet).
- OK to cap parity/null replication at n=2 unless promotion is at stake?
