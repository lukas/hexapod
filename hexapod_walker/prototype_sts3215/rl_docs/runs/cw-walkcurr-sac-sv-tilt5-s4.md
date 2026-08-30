# cw-walkcurr-sac-sv-tilt5-s4

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-08-30T04:32:17+00:00

**pod**: hexapod-mjx-train-10

**steps**: 20000000

**parent**: cw-walkcurr-sac-sv-tilt5-s1

**wandb_id**: glz9lm94

**hypothesis**: Plain English: seed lottery at the best dose -- SAC seed variance is the largest single effect this track has measured (seed 0 instant-topple vs seed 1 real six-leg stepping under an IDENTICAL config), and the tilt5 dose (the only config that ever kept stepping most episodes, fwd median 0.055m) has only ever been run on seed 1. Operator-ordered overnight population sweep (MCP operator lane 20260830T035139Z, Lukas: branch many rollouts on the idle fleet and select the best honestly): fresh seed 4 of the byte-identical SAC tilt5 recipe (clone of cw-walkcurr-sac-sv-tilt5-s1, WALKCURR_SV_TILT bank green at dose 5.0) at 10x the original budget (20M) -- levers are seed + budget only, read jointly with the s1-b20m extension (concurrent cycle, same operator order) and 2 sibling seeds as a 4-wide SAC population. Prediction-if-true: at least one seed both steps AND balances -- fall rate off 24/24, forward_dist past 0.06m and climbing, walk_speed in the 0.05-0.08 band with rising ep_len. Prediction-if-false: every seed reproduces the step-then-stumble ceiling (or seed-0-style instant topple) at 20M with flat reward -- the seed axis at this dose is closed and the fork moves to the structural anti-freeze/balance pretrain curriculum (STATUS candidate 1). Strongest alternative: only the extended seed 1 improves (consolidation, not seed lottery, is the lever).

**gate**: Rung-1 C-env det+sto fixed-forward panel (n>=6 each) at 20M: PASS needs progress_ratio >= 0.35, slip/m <= 3.0, gait_valid >= 4/6, falls on <= 1/6 det episodes. PARTIAL/continue (08-21): fall rate below 24/24 or forward_dist median clearing 0.06m with reward not declining. FAIL: seed-0-style instant topple or the unchanged 24/24 stumble ceiling at 20M with flat/declining reward. Discovery litmus per the corrected standard: env/walk_speed in the cmd band AND ep_len stable/rising AND over_current at background -- freeprog escape alone is the known artifact. Selection discipline (operator 08-30): no promotion from the search eval alone -- held-out eval/command seeds plus a replicate seed before any track-level claim.

**verdict**: SAC tilt5 20M continuation, seed4: does NOT escape the fall-then-stumble ceiling -- unchanged 24/24-fall signature, flat/declining reward. Evidence: DR-0 gate n=24, ALL 24 episodes end in a fall (TERM tilt_pitch/tilt_roll/over_current across all 4 sub-panels), fwd med 0.03-0.08m (walk/det 0.08, walk/sto 0.03, walk_startjitter/det 0.03, walk_startjitter/sto 0.04) -- at or below the s1-b20m/s1 baseline's already-measured ~0.055-0.07m ceiling, no clear escape; prog med negative on 3/4 sub-panels (-0.30 to -11.22), slip/m 2-11 (cap 3.0). Training curve: env/walk_speed reached the commanded 0.05 m/s band mid-run but reward peaked ~154 at 12-14M then declined to 149.05 by 20M (quarters [144.7,152.6,152.3,150.8], last-quarter dip) -- flat/declining, not the 08-21 continue case. Root cause visible in the mismatch itself: walk_speed is an in-rollout instantaneous/pre-termination metric, not held-out net displacement -- policy walks briefly then falls (tilt_pitch/roll) every episode, so training-side speed looks encouraging while eval-side progress stays pinned. Matches this run's own pre-registered FAIL text exactly (unchanged 24/24 ceiling, flat/declining reward) -- no anomaly, no dig-in trigger. Closes 3 of the operator's 4 tilt5-20M continuation arms as FAIL (s1-b20m FAIL, s2 FAIL, s4 FAIL); s3 also shows steps=20000000/finished with an ambiguous read (prog med clears 0.35 on all 4 panels, fwd 0.10-0.12m, but gait_valid 0/6 everywhere with sacrificed legs [0,3] present in nearly every episode -- looks like a leg-drag artifact inflating progress, not a real escape) but is NOT in this cycle's scope (not listed as finished for this cycle) -- left for whichever cycle owns it; do not treat this note as a track-wide close.

