# cw-walkscratch-easy0905-sde-s2-c2-dgatefix-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-05T16:58:49+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s2-c2-dgatefix

**hypothesis**: Plain English: on this one seed, walk_duty_gate=1.0 applied to sde-s2-c2's entrenched 40M leg-1-park exploiter is applying real, ungamed pressure (env/walk_duty_gate_factor genuinely declined 1.0->0.64 over 2M, never saturating at ceiling) while ep_rew_mean kept climbing the whole canary (94->224->332->406) -- unlike its remcost dgatefix siblings, whose reward got WORSE under the identical mechanism. Per the 08-21 ruling (rising reward + bad eval = continue, not a reflex fail), this tests whether a full acquisition-scale budget lets that pressure actually walk leg 1 back out of its 0.01-duty park and clear gait_valid, instead of closing the lever off a single under-budgeted 2M canary.

**gate**: ACQUISITION (40M): PASS if held-out walk/det harness gait_valid >=4/6 with duty_cycle>=0.10 on every leg (six legs really cycling, not just a slower decline). CONTINUE (do not close, extend or re-checkpoint) if gait_valid stays <4/6 but ep_rew_mean/env/walk_speed keep climbing and env/walk_duty_gate_factor keeps declining without re-saturating (misalignment still resolving per 08-21). FAIL (close this lever on this seed) if reward or speed collapses, the factor re-saturates at ceiling despite the persisting sacrifice, or a full-freeze substitutes for the park.

**refused_reason**: acquisition runs require --evidence: name the healthy canary and a comparable full-budget learning precedent.

