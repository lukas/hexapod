# Final corrected Cartesian ON/OFF read

2026-09-08T07:07:41.102229+00:00

Read-only exact24-episode `_gate/report.json` comparison. No mixed sessions, replay, rendering, verdict mutation, kick or launch. Owner063721 finished before this read; partial-refill070331 was active. OFF gate completed during this read; earlier CPU-finalizer state is retained in cpu_read.txt.

| Group |12M ON/OFF slip ratio|22M ON mean slip|22M OFF mean slip|22M ratio|ON gait/terms|OFF gait/terms|
|---|---:|---:|---:|---:|---:|---:|
|walk/det|2.4179|11.1797|5.4118|2.0658|4/6; 1|6/6; 0|
|walk/sto|3.0840|10.2138|5.4102|1.8879|6/6; 0|5/6; 0|
|walk_startjitter/det|2.5220|8.9030|6.1567|1.4461|4/6; 2|5/6; 0|
|walk_startjitter/sto|3.0968|11.9142|5.6455|2.1104|6/6; 0|6/6; 0|

ON gait20/24; OFF22/24. ON has3 new tilt_roll safety terminations versus0/24 at12M; OFF remains0/24. Only1/4 groups meets ≤1.5×; none exceeds3×. The final gate does not support promotion or another automatic extension. Health loss blocks continuation, and the final intermediate clause is exhausted. This is not broad Cartesian-class closure.

All four ON group means improve descriptively from12M, while OFF stays near its previous range and improves slightly. **Do not call that paired same-draw convergence:** only the first2/24 final ON/OFF randomization payloads agree. They diverge after ON’s first early termination because the evaluator reuses one env/RNG across resets. Prior12M ON/OFF and finalOFF/priorOFF match24/24 draws. The first new failure itself is in the still-matched second episode. Subsequent averages include different realized episode panels.

Evaluation metadata match across all four reports: mesh_mjx twin,0 meshes/91 geoms/4.80573kg;100Hz,4096counts/s,acc1000,3.6°slew;policy_std.135;seed0;DRscale0 with configured DR overrides;identical start-jitter panel. Training seed2, identical new10M budgets, own12M checkpoint parents; only effective cfg differences are the three Cartesian foot-box keys. Code snapshot hashes differ across sequential launches and are recorded rather than assumed identical.

The original12M gate required arithmetic means: ratios2.4179/3.08399/2.52204/3.0968 meant only2/4 above3×, supporting the prior intermediate classification. The final gate explicitly requires0 falls for promising and forbids another automatic extension on remaining intermediate results.

summary.json holds full precise means/progress, gate text, exact source paths, metadata/config comparisons, terminated-episode details, and draw-match booleans. Raw native report texts and parsed JSON are preserved.
