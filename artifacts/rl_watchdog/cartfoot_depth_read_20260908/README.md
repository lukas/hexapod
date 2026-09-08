# Independent fresh-Cartesian depth read

Read UTC: 2026-09-08 08:18:19 UTC. Read-only evidence for active formal triage owners; no run verdict, launch, rerender or shared-state mutation.

Eight exact `_gate/report.json` files were available: seed7 and seed11, Cartesian ON and joint-space OFF, each40M acquisition source and its +10M continuation. Each has24 episodes in four six-episode panels. Other name matches and mixed-session reports were excluded. “40M” and “50M” below are allocation labels; this task did not independently remeasure optimizer step counts.

## Registered depth gate versus health

| Seed | ON gait-valid source → continuation | OFF gait-valid source → continuation | Terms, all four reports | Continuation ON/OFF mean-slip ratios |
|---|---:|---:|---:|---|
|7|23 →11 /24|19 →12 /24|0|0.9936 /0.9692 /0.9715 /0.9348|
|11|23 →19 /24|12 →12 /24|0|0.8975 /1.0371 /0.9255 /0.9943|

Panel order throughout: walk/det, walk/sto, walk_startjitter/det, walk_startjitter/sto.

Both ON continuations satisfy their narrow registered mean-slip/fall predicate: ratio<=1.2 in4/4 panels, zero new terminations; neither hits >1.5 in any panel. This does not establish gait-health retention.

**Seed7: the matched control fails its own registered gait-retention condition.** OFF ordinary deterministic gait drops6/6→0/6 and start-jitter deterministic1/6→0/6, although means stay within its2.6–3.4/m slip band and there are zero falls. The OFF gate explicitly says control drift makes the paired ON/OFF read inconclusive. Therefore report: *slip/fall predicate retained, but the registered control-health proviso prevents a clean overall seed7 depth-retention conclusion*. Do not silently call this a full healthy HOLDS.

**Seed11: narrow registered slip/fall durability holds, with a separate ON gait regression.** OFF mean slip changes by−3.27%,−7.68%,−1.60%,−2.98%, within its registered±15% retention band; OFF gait remains12/24 with identical episode-level leg flags. ON loses four gait-valid episodes (23→19), so its narrow gate result is not six-leg health closure. The source OFF report is12/24, not18/24 inferred from a narrative shorthand; use the exact report.

## Per-leg changes

- Seed7 ON panel gait counts6/6/5/6→0/6/0/5. Leg4 flags expand from one start-jitter deterministic episode to all12 deterministic episodes plus start-jitter stochastic episode3. Leg1 also appears in start-jitter deterministic episode2.
- Seed7 OFF6/6/1/6→0/6/0/6. Leg4 flags expand5→11 episodes, leg1 flags1→3. This is a shared deterministic leg-use regression, despite stable slip and zero falls.
- Seed11 ON6/6/5/6→6/6/1/6. New failed start-jitter deterministic episodes0,2,3,5; source failure episode1 persists. Leg4 flags1→4, and leg1 flags0→1.
- Seed11 OFF0/6/0/6→0/6/0/6. Leg1 flags12 and leg4 flags11 at both depths, with exact episode-level flag retention.

No videos were rerendered or visually reviewed in this subtask. Do not label these flags benign or dismiss them as detector noise without independent evidence. Existing gait predicates were not changed.

## Means, medians and comparability

The gate explicitly uses arithmetic means of episode `slip_per_m`. `metrics.json` retains both means and medians separately; the ratios above use means only.

Mean-slip vectors source → continuation:
- Seed7 ON:2.7910/3.2197/2.7893/3.0950 →2.7950/3.2650/2.7800/3.0915.
- Seed7 OFF:2.8260/3.4115/2.8498/3.2567 →2.8130/3.3687/2.8615/3.3070.
- Seed11 ON:2.8940/3.3560/2.8118/3.3847 →2.6260/3.3903/2.6658/3.2080.
- Seed11 OFF:3.0250/3.5412/2.9272/3.3255 →2.9260/3.2692/2.8803/3.2265.

Every realized-randomization field matches exactly for each aligned parent→child episode and each aligned ON/OFF episode at both depths. All eight reports have identical reported model/motor/reset-panel identity and policy_std0.135: mesh_mjx_twin,0 meshes,91 geoms,4.80573kg,100Hz,4096counts/s speed/1000acceleration/3.6degrees-per-tick slew. Realized torque scale is3. This is the relaxed EASY assay, not nominal-torque/noisy physics, joystick qualification or the assisted full-mesh hardware-limit contract.

Identical reported metadata is not a substitute for source/XML/checkpoint hash identity; these report files do not provide a full independently verified code-and-asset provenance audit. The six nominal deterministic episodes can repeat an identical fixed draw;24 episodes do not imply24 independent randomized conditions.

Formal triage remains with existing owners. No new extension is recommended by this read; both clear narrow results and health/control caveats should be recorded before any separate experiment is considered.

## Files

- `reports/`: eight exact parsed gate reports.
- `metrics.json`: arithmetic means, medians, panel/aggregate gait counts, flags, parent/child ratios and realized-randomization comparisons.
- `registered_depth_gates.json`: unchanged registered gate/hypothesis text at read time.
- `identity.json`: reported identity and policy-standard-deviation comparisons.
- `provenance.json`: source paths, timestamp, selection and ownership limits.
