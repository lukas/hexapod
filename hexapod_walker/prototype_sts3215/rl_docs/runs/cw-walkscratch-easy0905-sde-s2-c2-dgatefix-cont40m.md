# cw-walkscratch-easy0905-sde-s2-c2-dgatefix-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-05T17:00:20+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s2-c2-dgatefix

**wandb_id**: 66wc8jin

**hypothesis**: Plain English: on this one seed, walk_duty_gate=1.0 applied to sde-s2-c2's entrenched 40M leg-1-park exploiter is applying real, ungamed pressure (env/walk_duty_gate_factor genuinely declined 1.0->0.64 over 2M, never saturating at ceiling) while ep_rew_mean kept climbing the whole canary (94->224->332->406) -- unlike its remcost dgatefix siblings, whose reward got WORSE under the identical mechanism. Per the 08-21 ruling (rising reward + bad eval = continue, not a reflex fail), this tests whether a full acquisition-scale budget lets that pressure actually walk leg 1 back out of its 0.01-duty park and clear gait_valid, instead of closing the lever off a single under-budgeted 2M canary.

**gate**: ACQUISITION (40M): PASS if held-out walk/det harness gait_valid >=4/6 with duty_cycle>=0.10 on every leg (six legs really cycling, not just a slower decline). CONTINUE (do not close, extend or re-checkpoint) if gait_valid stays <4/6 but ep_rew_mean/env/walk_speed keep climbing and env/walk_duty_gate_factor keeps declining without re-saturating (misalignment still resolving per 08-21). FAIL (close this lever on this seed) if reward or speed collapses, the factor re-saturates at ceiling despite the persisting sacrifice, or a full-freeze substitutes for the park.

**verdict**: Result: FAIL vs the ACQUISITION (40M) funding bar -- the entrenched-checkpoint dgatefix continuation does NOT rescue the gSDE leg-park exploit within a full 40M budget. Evidence: harness gait_valid 1/24 overall (0/6 walk/det, 1/6 walk/sto, 0/6 both startjitter modes), leg 1 chronically sacrificed in nearly every episode (occasionally leg 4 too), IDENTICAL walk/det numbers across all 6 episodes (prog 1.10, slip 4.45, fwd 1.36m -- deterministic dead-leg drag), frame strip (walk_det_0.png) visually confirms one leg trailing/dragging on the ground the whole clip while the other five cycle. W&B history over the full 40M run shows exactly the FAIL pattern this gate's own text called out in advance: env/walk_duty_gate_factor genuinely declined 1.0->0.62 through the first ~2M (the promising signal that licensed this continuation) but then MONOTONICALLY RE-SATURATED back up to 0.85-0.94 by 40M end -- the policy found a way to satisfy the duty floor again (via the trailing-window completion-scoring gap already diagnosed for this mechanism family) while ep_rew_mean kept climbing hugely (90->2100+) on the back of the other five legs' real work, and env/walk_speed stayed flat ~0.13-0.14 m/s the entire run (no genuine acceleration once the factor re-saturated). This is exactly the disqualifying condition named in the gate at launch: 'FAIL if... the factor re-saturates at ceiling despite the persisting sacrifice.' Why: confirms the walk_duty_gate mechanism's completion-scoring window is gameable by an ALREADY-entrenched exploiter given enough budget to search back to a satisfying schedule, not just by a fresh-init policy (closing the last live cell of that ambiguity). What's next: per CURRENT_TRUTHS.md (09-05 ~17:2x/17:3x), this was explicitly 'the one live exception' kept running as a sunk-cost read after the gSDE sub-lineage was otherwise closed 6/6 on every other repair mechanism/recipe; this FAIL closes the exception too -- the gSDE sub-lineage (bare-sde and sdehalfgrav-remcost) is now CLOSED end-to-end, zero further gSDE arms of any kind (fresh or entrenched-checkpoint, any repair lever) should be funded. Remaining walkcurr GPU budget belongs entirely to the working non-gSDE base/halfgrav heading-curriculum ladder (medhead rung now in flight both families).

