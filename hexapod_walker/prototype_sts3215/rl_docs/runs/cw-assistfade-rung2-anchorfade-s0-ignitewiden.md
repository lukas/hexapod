# cw-assistfade-rung2-anchorfade-s0-ignitewiden

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T17:07:12+00:00

**pod**: hexapod-mjx-train-4

**steps**: 8000000

**parent**: cw-assistfade-rung2-anchorfade-s0-reseed8m-gatefix

**hypothesis**: Plain English: does the rung-2 hardening ladder's speed-band-ignoring pathology (3/3 exploration-magnitude repairs closed this cycle: zero/1.65x/2x log-std boost all fail, the biggest boost even collapsing the gait) trace back to HOW ignition itself was run, not to insufficient exploration during the later hardening retrofit? Every prior ignition (this seed's own -reseed8m-gatefix included) ran the full 8M anchor-fade anneal at a single PINNED 0.06 m/s command the whole time -- the policy may have baked in one habitual stride amplitude/cadence before hardening ever showed it a varying command, and a late-stage exploration boost cannot undo 8M+ steps of that habituation. Single lever vs the exact reseed8m-gatefix ignition recipe (same bc_anchor_coef=3.0->0 anneal mechanism, same reward stack, same original 2M seed checkpoint via the untouched --init-from): widen goal.walk_speed_min_m_s/max_m_s from the pinned 0.06/0.06 point to the same 0.04-0.08 m/s uniform band the hardening arms used, from step 0 of the FULL ignition anneal (not a late retrofit) -- so the policy has to satisfy the anchor-fade + gait ignition bar under a varying command from the very start. No new reward mechanism (goal.walk_speed_min/max_m_s is an existing, already-used cfg knob), so no new semantics-bank pass is required.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS needs BOTH: (a) the standard rung-2 ignition bar (bc_anchor_anneal/gate_pass latches, bc_coef ramps to 0, post-anneal held-out det+sto 4-mode panel clears gait_valid 24/24-ish, 0 falls/terminations, progress_ratio>=0.35) exactly like reseed8m-gatefix's own PASS, AND (b) achieved speed_mean_m_s visibly covaries with cmd_dist_m/10s across the widened per-episode band (not clustered within ~0.005 m/s across the >=0.02 m/s spread, the exact pathology that survived every hardening-retrofit repair). FAIL-NO-IGNITION if the anchor never anneals or the gait/falls bar fails outright (the widened band is too hard to ignite on, revert to pinned-then-harden). FAIL-STILL-IGNORES if ignition passes cleanly but speed still clusters flat despite being trained on the varying band from step 0 -- this would close BOTH the exploration-magnitude AND the ignition-habituation theories, and point at a genuinely new mechanism (an explicit stride-amplitude/speed-tracking reward term) as the only remaining lever.

**refused_reason**: canary runs cap at 2000000 steps (asked 8000000): the question is 'is the training mechanism healthy?' - continue as --phase acquisition with --evidence.

