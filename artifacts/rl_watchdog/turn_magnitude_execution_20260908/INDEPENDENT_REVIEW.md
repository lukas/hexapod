# Independent result review

Reviewer: delegated `template_norm_review`, after execution, read-only. The reviewer inspected the preregistered design, frozen vectors, selected states, all raw JSON rows and summaries. It did not run the simulator, modify the criterion, regenerate metrics or rehash NPZ arrays. A separate publishing-agent NPZ comparison/current rehash is recorded in `postexecution_audit.json`.

**STOP is supported; no raw-row/summary mismatch was found.** All eight candidate gains, odd/even terms and comparator differences recompute exactly from the raw JSON metrics. None reaches 5 mrad; only two odd responses are positive. Comparative advantage is negative in every start-0 state and positive in every start-pi state, so no fixed pair repeats an advantage.

All 32 signed branches pass retention, complete 80 ticks, use the correct frozen five-tick vectors and record zero action-bound clipping. Exactly 50 rows exist: four baselines, 40 branches and six straight rollouts. Group membership and boundary lookup match the preregistered rule. Eight zero controls match recorded baseline prefix/endpoint/window hashes. Both straight triples match trace/endpoint/current hashes, complete 1500 ticks and pass post-ramp retention. Current records are complete for all 50 rollouts and explicitly labeled uncalibrated simulated estimates. Frozen vector, protocol and reference-baseline hashes match preregistration.

This result rejects the exact frozen allocation/mapping, not every magnitude-weighted controller. No follow-up trial was proposed or authorized by this review.
