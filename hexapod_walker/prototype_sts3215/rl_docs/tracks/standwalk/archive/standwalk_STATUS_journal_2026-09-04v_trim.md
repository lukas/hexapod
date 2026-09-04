# standwalk STATUS journal archive — 2026-09-04v (verbatim)

Moved verbatim from the top of STATUS.md when the combdose0p6-s1-r3
verdict closed the bc_anchor_walk_combined_dose axis 4/4 FAIL (whole
lever family 8/8 FAIL alongside the yaw-arm-scale geometry axis).

---

Update, 2026-09-04 ~00:1x (**Candidate (i)-v2 (yaw-arm-scale) dose x
seed grid now CLOSED 4/4 FAIL. New lever built + unit-tested + a
4-cell canary LAUNCHED to test the escalation path.**)

`yawarm1p5-s1` (seed1, dose 1.5) verdicted FAIL-MECHANISM, closing the
candidate (i)-v2 grid at 4/4 (seed0/1.5 FAIL, seed1/1.5 FAIL, seed0/2.0
FAIL, seed1/2.0 FAIL). `probe_turn_authority.py --vx-cmds` (full
84-key non-train cfg-set replayed, seed1 control re-verified fresh vs
the cached file — matched within noise): pure-turn `wz_med` (seed-avg)
+0.197/-0.188 vs seed1 control `cap29-stdwalklo-hi-s1` +0.226/-0.247 →
regression 12.6% (+) / 24.0% (-), BOTH over the 10% cap. Combined-tick
(`vx=0.08`) `wz_med` +0.106/-0.158 vs the seed1 control's own combined
read +0.087/-0.142 → BOTH signs beat the comparator cleanly (+22%/
+11%) — a clean bidirectional win, matching its seed0 twin (the only
other cell to win both signs; both dose-2.0 cells were sign-
asymmetric). No falls. Reward quarters `[25.6, 55.9, -190.7, 121.9]`,
final `ep_rew_mean` 167.97 — the same family Q3 dip/recovery shape,
not a collapse. FAILS on the regression clause alone, exactly
reproducing the seed0 twin's shape. Full verdict + evidence:
`rl_docs/runs/cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-
gradclip0p15-cap29-stdwalklohi-yawarm1p5-s1.md`.

**Read across all 4 cells:** every cell that wins the combined-tick
axis (both dose-1.5 cells, bidirectionally) blows the pure-turn
regression cap on the negative sign by 23-27%; cells that stay
near/under the cap on pure-turn (dose 2.0) lose the combined-tick win
instead (sign-asymmetric or outright worse). Combined with the
already-refuted omega-boost/omega-discount axis (both directions,
09-03), the WHOLE geometry/scaling-lever search for item 2 is closed:
no single-scalar open-loop dose clears the gate without trading away
pure-turn authority it isn't supposed to touch — the lever is bit-
exact on pure-turn BY CONSTRUCTION at the scripted-teacher level, so
the RL-trained regression must come from the SHARED dual-core policy's
representation being pulled by the combined-tick BC-anchor imitation
target, not the geometry.

**Escalation, built this cycle:** `train.bc_anchor_walk_combined_dose`
(env: `sim_env.py` tags a combined tick's target with
`info["bc_walk_weight"]=dose`; trainer: `bc_anchor.py` carries the
weight through a new per-row ring column `_bc_wwt` and computes the
walk-mode loss as a per-row-weighted mean via a new `_weighted_mse`
helper) — the untried CONTINUOUS middle between the already-refuted
extremes (1.0 = full anchor pull, legacy; 0.0 = full skip,
`bc_anchor_walk_combined_skip`, refuted). Default 1.0 = legacy, bit-
exact off (multiplying by exactly 1.0 is an IEEE-754 no-op — proven by
a dedicated bit-exact-parameter-match test, not just inspection). 9
new tests (env-level tagging + loss-level weighted-mse math +
bit-exact-off + the graded-middle behavior sitting strictly between
full-skip and full-weight) all green; full `test_bc_anchor.py` rerun
114/114 (105 prior + 9 new). This is a training/imitation-loss
mechanism, not a reward change, so — matching every other BC-anchor
lever in this family (omega-boost, combined-skip, yaw-arm-scale) —
it's gated by `test_bc_anchor.py`, not `test_task_semantics.py` (that
bank's own reward-return tests don't exercise this code path at all,
confirmed by grep). Snapshot pending this cycle's `snapshot.sh` run
(see commit log for the hash).

**LAUNCHED**: 2-dose (0.3, 0.6) x 2-seed canary respec'd from the
matched comparators `cap29-stdwalklo-hi{,-s1}` (no other cfg changes —
single-lever discipline): `cap29-stdwalklohi-combdose{0p3,0p6}{,-s1}`,
all 4 VERIFIED training on their pods (`combdose0p3`@train-4,
`combdose0p3-s1`@train-5, `combdose0p6`@train-11 all ledger-RUNNING;
`combdose0p6-s1`@train-1 confirmed training on-pod via `kubectl exec`
— `train_ppo_mjx` process alive with the correct
`train.bc_anchor_walk_combined_dose=0.6` flag — but the CONTROLLER-
side ledger entry was still stuck at `INTENT` when this cycle ended;
NEXT CYCLE: reconcile that one ledger row to RUNNING/verify progress
before triaging, the training itself is not in question). NEXT CYCLE:
read all 4 with `probe_turn_authority.py --vx-cmds` (full cfg replay)
against the SAME pre-registered gate shape as every prior cell in this
family (beat the matched control's own combined read on BOTH signs,
<=10% pure-turn/straight-walk regression vs that control) — read the
FULL reward curve first (rider c: the cap29 family's Q3 dip/recovery
shape is not itself a fail signal). Prior banner moved VERBATIM to
`archive/standwalk_STATUS_journal_2026-09-03u_trim.md`.

**1st cell read, 09-04 ~00:4x: `combdose0p3` (dose 0.3, seed0) —
CANARY FAIL-MECHANISM, same shape as the geometry-lever grid.**
`probe_turn_authority.py --vx-cmds`, full 84-key non-train cfg-set
replayed, seed-avg vs the matched control's own `combined_09-03` read:
combined-tick (`vx=0.08`) `wz_med` WINS both signs (+0.1313 vs ctrl
+0.1101 = +19.3%; -0.1854 vs ctrl -0.1701 = +9.0%), zero falls
(12/12) — but pure-turn (`vx=0.0`) `wz_med` REGRESSES past the 10% cap
on BOTH signs (+0.1964 vs ctrl +0.2230 = 12.0%; -0.2005 vs ctrl
-0.2501 = 19.8%), and straight-walk wz drift (`vx=0.08, wz=0`) flips
sign and grows (+0.0295 vs ctrl -0.0408). Training reward healthy
(quarters `[23.4, 70.4, -81.3, 145.6]`, final `ep_rew_mean` 264.7, the
family's known Q3-dip/Q4-recovery shape). Same root-cause read as the
geometry-lever grid: the regression traces to the SHARED dual-core
representation, not to whichever knob (geometry scale or now anchor
dose) is turned. Full verdict:
`rl_docs/runs/cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-
gradclip0p15-cap29-stdwalklohi-combdose0p3.md`.

**2nd/3rd cells read, 09-04 ~01:0x: `combdose0p3-s1` and `combdose0p6`
(seed0) — BOTH CANARY FAIL-MECHANISM, dose axis now 3/4 FAIL.**
`combdose0p3-s1` (dose 0.3, seed1): combined-tick `wz_med` wins both
signs (+0.1206 vs ctrl +0.0868 = +39.0%; -0.1533 vs ctrl -0.1369 =
+12.0%, seed1 control), zero falls, but pure-turn REGRESSES past cap
on both signs (+0.2023 vs ctrl +0.2279 = 11.2%; -0.1954 vs ctrl
-0.2459 = 20.5%) and straight-walk drift flips sign — numbers track
its seed0 twin within 1-2pp on every axis, ruling out seed noise.
Full verdict: `rl_docs/runs/cw-standwalk-stage2-dualbc6-turncap-
mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-combdose0p3-s1.md`.
`combdose0p6` (dose 0.6, seed0, verdicted by a concurrent cycle):
combined-tick benefit COLLAPSED vs dose 0.3 (positive sign flat at
+0.14%, negative sign a marginal +1.6%) while pure-turn regression got
WORSE (21.2%/18.5% vs dose-0.3's 12.0%/19.8%) — doubling the dose
spent more pure-turn budget for near-zero combined-tick return, a
non-monotonic/diminishing-returns confirmation of the same shared-
representation root cause, not a new failure mode. **Dose axis: 3/4
FAIL** (only `combdose0p6-s1` open). Its FIRST launch attempt never
trained (0 global_step for 1200s); the `-r2` retry (identical spec,
same pod `hexapod-mjx-train-1`) ALSO failed to train the same way
(vec-env up, warm-start loaded, then silent crash to W&B `crashed`
within ~25 min, no PPO iteration) — second death on the same pod.
Investigation (09-04 ~01:4x): `hexapod-mjx-train-1`'s node `g129004`
read `/proc/loadavg` 66-85 and sibling node `g142d86` read 140+ (heavy
ALL-TENANT contention on some nodes right now) vs `g131eec` at 8-10 —
read as node-load starvation during `host_workers=24` env-vec spawn,
not a spec/checkpoint defect (no other `train-1` run today failed this
way). Corrective per the second-death infra-escalation rule: relaunched
as `...-s1-r3` explicitly pinned to `hexapod-mjx-train-2` (node
`g131eec`, low load) via `respec --now --pod`; VERIFIED RUNNING 09-04
~01:5x. Full note: `rl_move/orchestrator/OPERATOR_QUESTIONS.md`
2026-09-04 ~01:4x entry. Do NOT launch the next escalation lever yet
— once `-r3` reads, if it also FAILs the whole
`bc_anchor_walk_combined_dose` axis closes 4/4 alongside the
geometry-lever axis, and the next lever must act on something neither
family reaches (phase-schedule the weight WITHIN a stride, or split
policy capacity so pure-turn gets a protected sub-path). If `-r3`
instead fails to TRAIN again on an uncontended pod, that rules out
node-load and reopens this as a real code/checkpoint dig-in.
