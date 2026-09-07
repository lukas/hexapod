# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2-widenrear180

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-07T20:07:38+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2-acq1

**wandb_id**: 692tv6qc

**hypothesis**: Plain English: widen8 (adding all 3 new rear/diagonal-rear headings +-135/180deg at once to the base 5-way set) closed ACQ FAIL 3/3 seeds with a NEW chronic front-pair (legs 0/5) sacrifice, generalizing the L1/L4 middle-pair pathology to a heading-DEPENDENT redundant-pair rule. CURRENT_TRUTHS (09-07 ~09:5x) explicitly licenses a heading-bisected NARROWER widen (not the full 8-way jump) without waiting for the still-unbuilt heading-conditioned role-aware mechanism. This tests the narrowest possible step: add ONLY ONE new heading (180deg, straight-back, the single most extreme/pure rear direction and the most different from every already-trained heading) to the same seeds own already-ACQ-passed 40M crutch-off checkpoint, 2M canary, single axis (goal.walk_heading_set 5-way -> 6-way), matching widen8s own precedent tier/init exactly.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM/BEHAVIOR CANARY (2M, matches widen8 tier): PASS if gait_valid stays majority (>=4/6 walk/det) with 0 falls and NO chronic (repeated across episodes) leg-0 or leg-5 sacrifice -- if true, a single new rear heading does NOT reproduce widen8s fingerprint, supporting an incremental one-heading-at-a-time widening strategy that avoids needing the role-aware mechanism yet. FAIL if the SAME chronic front-pair (legs 0/5) sacrifice reproduces even from just this one heading -- if true, the pathology is triggered by rear-heading CONTENT itself (not by training multiple new headings at once), so incremental widening cannot dodge it and the role-aware mechanism becomes mandatory before any further heading-set expansion. Either outcome is informative and closes/advances the widen8 fork named in CURRENT_TRUTHS 09-07 ~09:5x.

**verdict**: CANARY FAIL - MECHANISM: same result as its sibling seed s1-widenrear180, read together as the decisive pair. walk/det gait_valid 3/6 (below the required >=4/6 majority), CHRONIC leg-0 sacrifice at episode indices 0,1,5 (duty ~0.06-0.24 on leg0 vs 0.4-0.8 elsewhere); 0 falls; reward rose 37->229 through training. IDENTICAL fingerprint to s1 (independent training seed) at the SAME fixed-eval-RNG episode indices -- sac[0] at det/{0,1,5}, sac[3] at sto/1, sac[5]/sac[0] at startjitter-sto/{2,3} -- rules out seed noise and confirms the pathology is driven by heading CONTENT, not by how many new headings are added at once. Video (contact_sheet.png) shows one leg held retracted/off-ground the whole 20s episode. Per the pre-registered fork this closes the widen8 'incremental one-heading-at-a-time' escape route 2/2 seeds (s0 companion is owned by a concurrent cycle); the still-unbuilt heading-conditioned role-aware mechanism (CURRENT_TRUTHS 09-07 ~09:5x/~04:4x) is now mandatory before ANY further walk_heading_set expansion on this lineage.

