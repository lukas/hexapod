# Archived standwalk STATUS banner — 2026-09-03u (verbatim)

Moved here 2026-09-04 ~00:1x when the candidate (i)-v2 dose x seed
grid closed 4/4 FAIL (yawarm1p5-s1 was the last cell) and the new
phase-scheduled BC-anchor-dose mechanism/canary superseded this
banner. Current STATUS.md has the fresh Update.

# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-03 ~23:2x (**Candidate (i)-v2 dose x seed grid now 3/4
FAIL. Both dose-2.0 cells (seed0 AND seed1) are in: dose 2.0 is WORSE
than dose 1.5 on every axis — pure-turn regression grows and the
combined-tick win degrades from "clean both-signs win" (dose 1.5,
seed0) to sign-asymmetric-or-outright-losing. Only the seed1/dose1.5
twin (a concurrent cycle) remains to close 4/4.**)

`cap29-stdwalklohi-yawarm2p0-s1` (seed1, dose 2.0) verdicted FAIL-
MECHANISM. `probe_turn_authority.py --vx-cmds` (full 84-key non-train
cfg-set replayed against a FRESH seed1 control run — the cached 17:19
seed1-control probe predates the probe-usage-gotcha fix and was NOT
reused, per this ledger's own gate text "read against the seed1
control instead"): pure-turn `wz_med` (seed-avg) +0.207/-0.180 vs
seed1 control `cap29-stdwalklo-hi-s1` +0.226/-0.247 → regression 8.3%
(+, inside the 10% cap) / 27.4% (-, blows it) — same shape as every
sibling cell (the negative side always breaks first). Combined-tick
(`vx=0.08`) `wz_med` +0.109/-0.136 vs the seed1 control's own combined
read +0.087/-0.142 → positive side beats cleanly (+26%) but negative
side is WEAKER than its own control (-4.5%) — sign-asymmetric, same
failure shape as combskip/omegaboost/yawboost-lodose, and a step down
from dose 1.5's clean bidirectional win. No falls on any turn row
(12/12); reward quarters `[23.5, 59.3, -200.6, 116.8]`, final `ep_rew_
mean` 164.6 — same Q3 dip/recovery shape, weakest final value of the
four cells so far but still positive/still climbing in Q4, not a
collapse. FAILS both gate clauses. Combined with the already-verdicted
`yawarm2p0` (seed0, dose 2.0: pure-turn regression 22.7%/25.0%, BOTH
over cap; combined-tick sign-asymmetric, positive side actually below
the control's own read) and `yawarm1p5` (seed0, dose 1.5: clean
bidirectional combined win, but regression 11.7%/25.4% still blows the
cap), the dose x seed grid is now 3/4 FAIL, with a clear dose-response:
1.5 is the family's best cell (only one to win combined on both signs)
and 2.0 is strictly worse on every measured axis at both seeds tried.
Only `yawarm1p5-s1` (seed1, dose 1.5, a concurrent cycle's run as of
this writing) remains. Full verdict + evidence: `rl_docs/runs/cw-
standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-
cap29-stdwalklohi-yawarm2p0-s1.md`, `logs/ckpt_eval/probe_turn_
authority_yawarm2p0_s1_combined_09-03.json` vs `logs/ckpt_eval/probe_
turn_authority_cap29_stdwalklo_hi_s1_combined_09-03_fullcfg.json`.

**PROBE-USAGE GOTCHA (still logged, not yet a code fix — see prior
banner, archived below, for the full writeup):** always replay the
FULL non-`train.*` cfg-set from the checkpoint's own training command
for any `probe_turn_authority.py --vx-cmds` read; the 5-flag shorthand
silently freezes the policy. This cycle additionally re-ran the seed1
control fresh under the full cfg rather than trusting the pre-gotcha
17:19 cached file, since that file's provenance (shorthand vs full)
was never logged at write time.

**NEXT CYCLE:** read the `yawarm1p5-s1` twin once available (it may
already be verdicted by its concurrent cycle by the time you read
this — check `rl_docs/runs/...yawarm1p5-s1.md` and the ledger status
before re-deriving anything). If it also FAILS (likely, given the
dose-2.0 pattern and the seed0/dose1.5 cell already failing on the
regression clause alone), candidate (i)/(i)-v2 and the whole
omega/yaw-arm-scaling axis close 4/4: no single-scalar dose on this
lever clears the pure-turn cap without giving up the combined win, at
either seed. Item 2 should then escalate to a structurally different
lever (phase-scheduled BC-anchor strength, per the redesign spec's
next class) rather than another dose/seed on the same mechanism — do
NOT pre-launch that new mechanism before the 4th cell confirms; it is
new reward/task-mechanism work and needs its own `test_task_
semantics.py` bank pass before any training launch regardless. Prior
banner moved VERBATIM to `archive/standwalk_STATUS_journal_2026-09-
03t_trim.md`.
