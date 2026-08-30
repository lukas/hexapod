# cw-walkcurr-pf-decleg-antifreeze-pretrain-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-08-30T05:56:05+00:00

**pod**: hexapod-mjx-train-1

**steps**: 3000000

**parent**: cw-walkcurr-pf-decleg-sv-s0-rr3

**hypothesis**: Plain English: a from-scratch policy in this diet always ends up in a static-quiver-to-over_current basin (4/5 decleg-b100m population-sweep arms now FAIL'd this exact way this cycle); this tests whether a short PURE step-completion pretrain phase (no freeprog/body-speed income at all, ONLY the already-validated k_step_event term -- which pays a leg NOTHING unless it completes a real >=10mm-along-command lift-swing-touchdown, so a quiver/fidget in place literally cannot earn anything, unlike a raw-|qvel| anti-freeze bonus which the track's own idle-terminate mechanism already showed gets gamed by fidgeting, WALKCURR_PF_IDLE_TERM/idleterm1-3, 08-24) can dislodge the basin before the normal freeprog diet ever turns on. New bank WALKCURR_SV_PRETRAIN_STEP (test_task_semantics.py, 4/4 green) proves gait >> park/stall/belly_sit/reverse/sideways (all pose-invariant near a common floor, no fidget dodge) and topple is the strict floor under this exact diet. This decleg-architecture half of a 2-arm pair (central sibling launched alongside) is a short 3M PRETRAIN phase only -- fresh random init, matching the track's rule-(a) (no BC/imitation/motion-prior warm-start; this is a same-diet-family RL reward-curriculum stage, not imitation). Prediction-if-true: env/walk_speed or walk_freeprog-analog leaves the static floor, ep_len_mean stable/rising, terminations/over_current at background, and video shows real leg lift-swing-touchdown cycling by 3M. Prediction-if-false: the policy still converges to a static/quiver basin (step_event never fires enough to matter) -- pretrain-staging is refuted alongside every other anti-freeze mechanism tried, and the ONLY remaining candidate becomes a non-PPO search method (matches the CPG track's already-DONE direct-optimization approach, out of walkcurr's own founding-rule scope) or an operator [prior-free constraint] escalation. If PASS: queue phase-2 (--init-from-source into the standard WALKCURR_SV diet, freeprog back on) as the next-cycle continuation.

**gate**: Own-cfg health read (not a formal C-env gate -- this is a 3M PRETRAIN phase, not an acquisition run): env/walk_speed or a step/swing-completion proxy leaves its all-arms-FAIL static floor, rollout/ep_len_mean stable-or-rising (not collapsing), terminations/over_current at background not climbing, video shows real per-leg lift-swing-touchdown cycling (not just a bigger quiver). PASS on this read licenses an --init-from-source phase-2 continuation into the standard WALKCURR_SV diet (freeprog back on, budget matching the population-sweep's own 20-100M range); FAIL closes the pretrain-staging fork alongside idle-terminate/park_duty/RND/tilt/terrain/idle-charge.

**refused_reason**: discovery runs cap at 2000000 steps (asked 3000000): the question is 'did qualitatively correct behavior emerge?' - continue as --phase hardening with --evidence.

