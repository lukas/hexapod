# cw-walkscratch-crutchoff-s1-widen8-legdutyratio-guardfix-acq10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-08T01:13:19+00:00

**pod**: hexapod-mjx-train-0

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-widen8-acq1-legdutyratiofresh-guardfix1

**hypothesis**: Bounded +10M acquisition after the corrected 2M additive leg-duty-ratio canary passed its pre-registered mechanism-health gate: 21/24 gait_valid,0/24 terminations; every leg's episode-aggregate peer-relative duty exceeds0.22 in at least22/24 episodes. Actual activation is verified in W&B tdpmyt9z,charge=-150*shortfall. This is an emerging-underuse prevention/duration test, NOT proof that the charge repaired an entrenched gait: the ACTUAL initial checkpoint s1_widen8 itself scored21/24, and the same-budget undosed infrastructure-invalid arm scored22/24. Continuation tests whether learning on the active additive reward preserves six-leg use over acquisition where prior undosed long training entrenched sacrifice. Initialize from EXACT corrected guardfix1 output (MD5edfa283302954b40103334227eb3db1c), RNG3 (s1 is lineage label), same8-way headings, pure prior-free/noBC/no gait clock, unchanged reward150/target.30/grace3/tau1 and source motor/DR contract. Single planned seed, no additional arm, no relaxed qualification.

**gate**: ACQUISITION duration read, +10M only. Compare the exact24episode det/sto walk/startjitter panel to corrected2M source and actual undosed initialization, reporting per-leg duty ratios, gait_valid, progress and slip by group. Retain original health bar:0 new falls/terminations, gait_valid>=18/24 and formerly weak leg relative duty>=0.22 in a majority of episodes. A claimed mechanism improvement additionally needs behavioral improvement over source, not reward alone; an unchanged21/24 is retention, not efficacy proof. If new falls or persistent gait/command regression emerge, inspect and stop per existing pruner rules, preserving checkpoints. Rising charge/reward cannot excuse worsening behavior. Read intermediate behavior at normal existing eval cadence; any further budget needs a fresh measured justification. Original final walking/joystick qualification remains unmet and unchanged.

**refused_reason**: acquisition runs require --evidence: name the healthy canary and a comparable full-budget learning precedent.

