# cw-robotwalk-turns-20260906-cont8m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T04:49:32+00:00

**pod**: hexapod-mjx-train-5

**steps**: 8000000

**parent**: cw-robotwalk-turns-20260906

**hypothesis**: Plain English: the first 8M of turn-income training kept the walk healthy (zero falls, full gait_valid, slip cut roughly in half vs Candidate B on the matched cmdsuite) but did not yet clear its own pre-registered turn-tracking bar, and training reward was STILL RISING every quarter (337->1136->1917->2418, not plateaued) when the budget ran out -- so give it another 8M on the identical recipe before judging the turn-income mechanism, per the 08-21 rising-reward-continue ruling. Fresh matched-cell reads this cycle: joygate stress_mix course_err_1s_med 8.55deg (Candidate B's own recorded 5.17deg bar NOT yet met), cmd_suite tip-left/tip-right wz_err 0.108/0.100 (modest edge over a FRESH Candidate B re-read at 0.124/0.155 on the identical cells, but neither model clears the literal <0.076 absolute bar), fwd/back/left/right/arc slip/m 1.49-1.94 (much better than fresh Candidate B's 2.70-3.74 on the same cells -- walking quality genuinely improved, not just retained). Prediction-if-true: continued training brings course_err_1s_med down toward/under 5.17deg and widens the tip-turn edge over Candidate B, while walk retention (prog_m, slip, gait_valid, zero falls) holds. Prediction-if-false: course_err and turn wz_err plateau at today's level with reward still rising (== reward/eval misalignment on the turn axis specifically -- audit the yaw reward terms next, do not clone seeds) or reward itself plateaus/falls (== recipe ceiling, retreat to a softer/differently-timed turn-income dose).

**gate**: ACQ 16M total, campaign robotwalk-smooth-20260906 continuation: same 4 clauses as the parent's own gate (turn-beats-Candidate-B on tip_ccw/tip_cw wz_err_med both signs + combined walk+turn read; walking retained det all-8-heading zero falls/prog_m>0/fwd>=0.29m/12s/slip<=2.9/no sacrificed legs; joygate stress_mix course_err_1s_med <= Candidate B's fresh-read baseline (this cycle's matched re-run: 5.17deg historical / 8.55deg is this run's own pre-continuation number to beat); translation cells require real progress). PASS only if course_err_1s_med clears 5.17deg (or at minimum drops meaningfully below this run's own 8.55deg pre-continuation baseline) AND tip wz_err_med on both signs improves vs this run's own pre-continuation numbers (0.108/0.100) without walk retention regressing. Flat-or-worse on course_err/tip wz_err with reward still rising = misalignment, audit the yaw reward terms next. Reward plateaued/falling = recipe ceiling, do not clone further same-recipe seeds.

