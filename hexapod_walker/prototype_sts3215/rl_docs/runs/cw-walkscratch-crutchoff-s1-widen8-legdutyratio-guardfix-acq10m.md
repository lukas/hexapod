# cw-walkscratch-crutchoff-s1-widen8-legdutyratio-guardfix-acq10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-08T01:14:58+00:00

**pod**: hexapod-mjx-train-0

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-widen8-acq1-legdutyratiofresh-guardfix1

**wandb_id**: xy81bl5d

**hypothesis**: Bounded +10M acquisition after the corrected 2M additive leg-duty-ratio canary passed its pre-registered mechanism-health gate: 21/24 gait_valid,0/24 terminations; every leg's episode-aggregate peer-relative duty exceeds0.22 in at least22/24 episodes. Actual activation is verified in W&B tdpmyt9z,charge=-150*shortfall. This is an emerging-underuse prevention/duration test, NOT proof that the charge repaired an entrenched gait: the ACTUAL initial checkpoint s1_widen8 itself scored21/24, and the same-budget undosed infrastructure-invalid arm scored22/24. Continuation tests whether learning on the active additive reward preserves six-leg use over acquisition where prior undosed long training entrenched sacrifice. Initialize from EXACT corrected guardfix1 output (MD5edfa283302954b40103334227eb3db1c), RNG3 (s1 is lineage label), same8-way headings, pure prior-free/noBC/no gait clock, unchanged reward150/target.30/grace3/tau1 and source motor/DR contract. Single planned seed, no additional arm, no relaxed qualification.

**gate**: ACQUISITION duration read, +10M only. Compare the exact24episode det/sto walk/startjitter panel to corrected2M source and actual undosed initialization, reporting per-leg duty ratios, gait_valid, progress and slip by group. Retain original health bar:0 new falls/terminations, gait_valid>=21/24 (flat-or-better than this corrected source), no NEW chronic single-leg sacrifice versus the source panel and formerly weak leg relative duty>=0.22 in a majority of episodes. A claimed mechanism improvement additionally needs behavioral improvement over source, not reward alone; an unchanged21/24 is retention, not efficacy proof. If new falls or persistent gait/command regression emerge, inspect and stop per existing pruner rules, preserving checkpoints. Rising charge/reward cannot excuse worsening behavior. Read intermediate behavior at normal existing eval cadence; any further budget needs a fresh measured justification. Original final walking/joystick qualification remains unmet and unchanged.

**verdict**: CANARY PASS (acquisition-duration/retention scope, per its own pre-registered gate): +10M continuation of the charge-on (150) leg-duty-ratio-charge fresh-init recipe from the corrected 2M guardfix1 source (MD5edfa2833...). Held-out 24-ep det+sto walk/startjitter panel: gait_valid 22/24 (walk/det 6/6, walk/sto 6/6, sj/det 6/6, sj/sto 4/6), 0 falls/terminations in every mode -- flat-or-BETTER than the source's own 21/24 (source's sole det/0 sacrifice [leg5] flips to gv=True here; the same 2 startjitter/sto episodes [leg5 ep2, leg0 ep3] remain the only fails, no NEW chronic leg). Per-leg peer-excluded duty ratio for both formerly-weak legs (0,5) clears >=0.22 in 23/24 episodes each, same magnitude as source's 22-23/24 -- no regression. ep_rew_mean falling to -32103 (quarters monotonically more negative) is FULLY explained by rollout/ep_len_mean rising 483->1638->1970->1982/2048 (episodes surviving longer under a roughly-flat per-tick charge), not behavioral collapse -- matches the mechanism's own documented reward-vs-len pattern (SKILLS.md). This confirms the charge-on recipe survives a 5x-longer acquisition without new falls or new chronic sacrifice. It does NOT by itself prove the charge is the active ingredient of the +1-episode improvement (could be duration alone) -- that requires the matched charge=0 control (offctrl10m, root-owned, still training; untouched here). Next: read offctrl10m's own gate against this exact panel before claiming charge-specific efficacy.

