# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widenbis180-legdutyfresh

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-07T22:03:01+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widenbis180

**wandb_id**: d3qlhag1

**hypothesis**: Plain English: 4th arm of the from-scratch legdutyterm dose disambiguation (see s0-widen8-acq1-legdutyfresh's hypothesis), on the OTHER already-entrenched lineage (widenbis180, base5+ONLY the 180deg heading) -- does having the per-leg minimum-duty TERMINATION present from the START of training prevent the chronic leg-0 sacrifice from ever forming, instead of failing to repair it after 40M steps of habit like the just-closed s0-widenbis180-legdutyterm1 retrofit FAIL? Byte-identical to the original widenbis180 40M run (same seed, same --init-from the pre-widen medhead champion) with only the 5 walk_leg_duty_terminate/_penalty cfg-sets added from step 0. Queued to backlog (no launch cap left this cycle); drain onto the next free slot.

**gate**: PASS if gait_valid across the 24-episode panel is majority-clean (>=18/24, matching the pre-widen/medhead baseline band), no chronic leg-0 sacrifice recurring across most eval draws, 0 new falls vs the undosed widenbis180 baseline, and walk_leg_duty_terminate firing rarely/not-at-all by the end of the 40M. FAIL if the same leg-0 chronic sacrifice still forms by 40M regardless of whether the termination is firing frequently or has gone quiet.

**verdict**: FAIL (dig-in) -- the apparent trio-breaking improvement dissolves: it is inside eval noise, the same leg-0 sacrifice still forms at 40M, and the termination never quiets. Evidence vs the undosed s0-widenbis180 baseline (itself a confirmed FAIL): gait_valid 20/24 vs 18/24 and sacrifice-episodes 4/24 vs 6/24 are both Fisher exact p=0.72 on the 24-ep panels -- not a claimable delta -- and the sacrificed-leg identity is identical (leg-0 in 4 vs 5 eps, leg-5 in 1 vs 1). Video: walk/det/0 crawls with the front leg held aloft across the entire strip; walk/det/4 sits pinned near-stationary (fwd 0.18m). The dose adds pure cost: walk_leg_duty_terminate cuts 8/24 gate episodes early (baseline: 0 terminations) and its in-training firing RISES ~80 -> 132-143/log-interval through 40.37M -- the policy pays the termination as ambient price instead of learning balanced duty, the same shape as all 7 failed siblings. No real falls in either run (roll_class=fell is the term-reason taxonomy artifact; peak rolls 8-17 deg). This CLOSES safety.walk_leg_duty_terminate_s at 0/8 (4/4 legdutyterm1 retrofit + 3/3 widen8-acq1 fresh + this widenbis180 fresh): termination-as-price is the wrong mechanism shape for the front-pair sacrifice pathology on BOTH lineage severities; no viable niche. Next structural lever per track STATUS: a role-aware/heading-conditioned per-leg utilization TARGET (reward shaping toward balanced duty, not a cutoff); any further termination-shaped variant (incl. the rel-floor add-on currently in the working tree) needs a hypothesis for why it changes the incentive SHAPE, not just the floor arithmetic.

