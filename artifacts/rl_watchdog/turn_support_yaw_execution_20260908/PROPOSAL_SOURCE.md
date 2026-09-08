# Prepared proposal: support-conditioned geometric yaw burst assay

Status: prepared design candidate only. Not preregistered, executed, queued, or dispatched. The completed coordinated phase-template screen remains STOP. This proposal authorizes no PPO, recurring controller, physical robot action, or hardware deployment. Main walking task and any active DIG-IN ownership must be checked before dispatch; do not duplicate an existing investigation.

## Rationale and existing evidence limits

The completed coordinated screen qualified only its negative-yaw phase 0 template at amplitude 0.05 across both starts; neither global dose supported both yaw signs. Fifteen of 16 positive-vector cases had positive odd response and 30/32 pulse branches retained behavior. These observations motivate investigating state dependence but do not establish that support conditioning will help.

The reviewed single-joint bank stores qpos and complete-state hashes, but not raw pre-burst observations, qvel or normal-load masks. Per-foot loaded durations are 80-tick aggregates and cannot identify support at pulse onset. The existing runner reads per-tick touch sensors and pad geometry, and _ContactAudit captures per-substep normal forces. Exact prefix replay must export the proposed support observation. Do not infer stance labels from aggregate loaded durations or fit new response templates on the original eight states.

## Frozen inputs and held-out panel

Retain the reviewed bank's checkpoint, full-mesh XML/assets and 64-key configuration. Assert 34 meshes, 159 geoms, 4.80573 kg, and motor contract: write_speed 400, write_acc 20, slew0.375degrees/tick, resolved velocity ceiling 350 counts/s, 100 Hz. The 350 value is a velocity ceiling, not a current limit. Preserve all current and safety settings.

Introduce only the existing evaluation reset panel: start_jitter_deg=3, start_bad_prob=0.25, start_bad_max_joints=1, start_bad_deg_min=8, start_bad_deg_max=16. Use the first reset generated with diagnostic RNG seeds 1 and 2; publish actual offsets before nonzero branches. These are held-out simulation reset draws, not training seeds. Pair each reset draw across every other condition without changing its offsets; retain exact deterministic reset/replay provenance and controller state.

Cross product:
- 2 reset draws.
- 2 initial phases: pi/2 and 3pi/2.
- 2 yaw commands: wz=+0.15 and -0.15, with vx=0.08.
- 2 actual target phases: 5pi/6 and 11pi/6.

This is 16 branch states, 8 continuous baselines, and 48 branches (zero/positive/negative). Preserve the original 1 second hold and 1 second command ramp. Among pre-action ticks 600 through 674 inclusive, select minimum circular distance to each target phase; exact ties select earliest tick. Freeze these 16 selections from the 8 continuous baselines, each 755 ticks long, before executing nonzero branches. Early terminations or unavailable states remain reported failures; do not replace reset draws or selected ticks.

## Support observation without solver refresh

At each selected pre-action boundary:
1. Copy the live MjData into a private diagnostic copy, retaining already-solved contacts and constraint forces. Read stored contact wrenches using mj_contactForce. Do not call mj_forward or another solver evaluation on either live data or this force copy.
2. Sum positive normal force over external pad-ground contacts for each foot. Support means strictly Fn>0.5N. Record the solved observation timestamp and age: this is the last completed physics step's support observation, not a newly solved endpoint contact state.
3. Compute each supporting foot's normal-force-weighted contact point and express it in that pad's local frame using the same solved contact geometry.
4. Use a second private copy for endpoint kinematics only, following the established mj_kinematics/mj_comPos approach. Transform each material contact point into the endpoint world frame and compute its point Jacobian there. Do not recompute private contact forces. Do not alter live sensor history, controller history, solver state or RNG.

Thus delayed solved support observations and current endpoint geometry are distinguished explicitly. Snapshot/trace parity must verify that the diagnostic path is observational.

## One geometry-derived action law, with no response fit

Use world vertical z=(0,0,1), consistent with the original world-yaw outcome. Let r_i be the endpoint material contact point minus endpoint chassis origin, in world coordinates. Desired supporting-foot displacement direction per unit positive body yaw is b_i=-z cross r_i. Its vertical component is zero. Non-supporting legs receive zero increments.

For each supporting leg, obtain the3 × 3 world-position Jacobian J_i at that material point using its three hinge velocity addresses from the existing joint mapping. Convert to normalized-action coordinates through the actual affine decoder derivative: A_i=J_i diag(_HALF_RAD_i), including any logical-to-MuJoCo derivative/sign conversion. Assert that the frozen assisted decoder remains non-Cartesian and non-boxed. Do not silently assume joint ordering or an identity coordinate conversion.

Solve by truncated SVD. Retain singular values strictly greater than max(1e-10,1e-6*sigma_max), in metres per normalized-action unit. Each selected leg Jacobian must have rank 3 at this fixed cutoff. If any selected leg has rank below 3, the entire burst is unavailable and produces a recorded all-zero vector; do not compute a lower-rank substitute or change the cutoff.

Also require at least 3 supporting feet and rank 2 of the centered horizontal support-point matrix, with the same fixed absolute/relative numeric cutoff in its appropriate metre units. Below3 feet, rank-deficient support geometry, missing/nonfinite observations, any rank-deficient selected leg Jacobian, or a zero solution produces an explicitly recorded all-zero vector. These are controller availability rules, not new locomotion qualification gates. Do not replace unavailable states.

Assemble the 18-coordinate solution, multiply by sign(wz), then normalize globally as u=0.05*solution/max(abs(solution)). This is one maximum per-coordinate dose; record L1 and L2 norms. No template, coefficient, sign, support rule, phase rule or amplitude is fitted to response data. Exact wz=0 returns an all-zero vector.

## Three paired branches per state

From the same identical prefix, freeze the same u once:
- Zero: unchanged policy.
- Positive: add +u for exactly 5 control ticks.
- Negative: add -u for exactly 5 control ticks.

The commanded yaw remains unchanged in all three branches. Add perturbations after SB3 prediction clipping, then clip to action bounds before ordinary environment safety, servo processing and physics. Follow with 75 unchanged-policy ticks, giving the original 80 tick scoring window. Do not recompute the vector/support during the burst. Record actual applied increments and clipping. Positive and negative branches are symmetric requested perturbations, not a claim that realized joint motion is symmetric.

## Exactness and fixed behavioral decision

All zero branches must match their continuous baseline in full integration/controller state and trace. Every pulse prefix must match. Preserve original last-solve yaw as primary; true endpoint yaw remains an additional diagnostic. Missing/nonfinite metrics invalidate interpretation rather than defaulting to healthy values.

A positive branch qualifies only if all original conditions hold:
- G_plus=sign(wz)*(yaw_plus-yaw_zero)>=0.005rad.
- Positive baseline body-forward distance and branch forward>=0.9baseline.
- Loaded material contact displacement<=1.25baseline.
- Relative roll and pitch maxima<=baseline+3degrees.
- Complete 80 ticks, all walking, no termination.
- Its opposite-vector branch also satisfies corrected retention.
- Odd response (G_plus-G_minus)/2>0.

For each yaw sign, at least one of the two prespecified target-phase neighborhoods must qualify across all four reset-by-initial-phase combinations. Report every state; do not regroup after observing outcomes. No-op states cannot qualify. Preserve the original 5 mrad/retention rules; do not introduce a chronic-leg threshold. Report leg usage, support, current, clipping, action norms and both odd/even response descriptively.

Separately evaluate the four reset-by-initial-phase straight-command cells for 15 seconds. Exact wz=0 maps to zero and must reproduce untouched-policy full state and trace. This is a zero-off parity check, not new evidence of learned straight walking.

## Finite interpretation and ownership

A pass establishes held-out burst authority of this one analytic law. It does not establish that support conditioning itself caused the improvement, validate recurring closed-loop steering, or license PPO. A failure closes this law as specified. No automatic alternate masks, rank cutoffs, doses, templates, reset replacements, recurring schedules or training arms follow.

Before execution, root must inspect live main-walking/DIG-IN ownership and coordinate any existing investigation. If this diagnostic is unowned, root can assign it under standing simulation authority. This is a duplicate-work check, not a new request for human permission. Preserve the completed coordinated-screen STOP. This document is only a prepared proposal until an owner explicitly freezes and preregisters it before its own execution.
