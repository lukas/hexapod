Prior update (09-04 ~14:1x, idle-kick, no GPU spend): executed item-2's
own order to re-score the 6-lever-family FAIL wall vs matched
continuations — pure CPU analysis (`probe_turn_authority`, zero
training), filled 3 missing reads, reused existing 09-03/09-04 files
for the rest, re-scored all 10 seed0 + 10 seed1 lever cells against
`cont`/`cont-s1` (matched 2M plain-continuation, zero-lever controls)
instead of the frozen `cap29-stdwalklo-hi{,-s1}` baseline the original
gates used. **Real fork, not noise:** seed0 stays 9/10 FAIL (only
`yawarm1p5` clears combined-both-signs-win + <=10% pure-turn), but
**seed1 flips 5/10 to PASS** (`yawarm1p5-s1`, `yawarm2p0-s1`,
`omegaboost1p5-s1`, `omegaboost2p0-s1`, `combdose0p3-s1`: combined wins
both signs +4.5% to +53%, pure-turn worst -11% only for the one
exception `yawboost6p0-s1`). Corroborates the `selomegaboost4p0-s1`
asymmetry (09-04 10:0x) across 5 more families — likely `cont-s1` is
itself a weaker floor than `cont` (own pure-turn/combined wz_med
0.152/0.105 vs 0.172/0.132) — but every median is still only 2 probe-
seeds wide. Does NOT overturn any run's own verdict (each was scored
correctly against its own pre-registered gate); says the frozen-parent
comparator was the wrong yardstick for the seed1 half. Landed the
re-score as a real tool (not a throwaway script), tests green:
`rl_move/sim/rescore_turn_authority.py` (`cfg <run>` replays a
checkpoint's own non-`train.*` cfg-set from the ledger — no more
hand-copying, the exact gotcha that bit 09-03's yawarm triage;
`table <manifest.json> <control> [<control_s1>]` reproduces the table
above verbatim over `logs/ckpt_eval/probe_turn_authority_*_combined_
09-0{3,4}.json` + `cont`/`cont-s1`), `rl_move/tests/
test_rescore_turn_authority.py` (6 tests). Snapshot: see RL_LOG.
DIG-IN owed before any relaunch — see Next item 2's falsifier.

Prior update (09-04 ~13:2x, `mlcontprice8` k=8.0 CANARY FAIL-MECHANISM
but dose-responsive/real fix, residual own-DR fires NOT an entry-
window artifact) archived verbatim in this cycle's journal copy below.
