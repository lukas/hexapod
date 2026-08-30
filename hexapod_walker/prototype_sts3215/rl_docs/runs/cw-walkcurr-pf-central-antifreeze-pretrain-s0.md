# cw-walkcurr-pf-central-antifreeze-pretrain-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-08-30T05:58:34+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkcurr-pf-central-sv-s0-rr2

**wandb_id**: aasqq9xj

**hypothesis**: Plain English: matched centralized-architecture twin of cw-walkcurr-pf-decleg-antifreeze-pretrain-s0 (see that run's hypothesis for the full design rationale: a pure step-completion-only pretrain diet, fidget-resistant by construction via k_step_event's >=10mm-along-command lift-swing-touchdown gate, tested against the static-quiver-to-over_current basin every SV-wave arm (decleg AND central) has hit). New bank WALKCURR_SV_PRETRAIN_STEP (test_task_semantics.py, 4/4 green). Fresh random init, 2M PRETRAIN phase only, matching rule (a). Prediction-if-true/false: identical to the decleg sibling's -- read jointly as a 2-architecture pair (if only one escapes the basin, architecture is the confound, not the mechanism).

**gate**: Same own-cfg health read as the decleg sibling: env/walk_speed off the static floor, ep_len_mean stable/rising, terminations/over_current at background, video shows real per-leg cycling. PASS licenses phase-2 --init-from-source continuation; FAIL (matching decleg) closes the pretrain-staging fork.

**verdict**: Matched centralized-architecture twin of decleg-antifreeze-pretrain-s0 -- IDENTICAL numbers (env/reward_step_event ~0.0007, env/walk_speed 0.0203, walk_direction_err_deg 89.8deg, ep_len_mean 547.29, terminations/truncated=153, ep_rew_mean 202.03 == the scripted 'park' floor in WALKCURR_SV_PRETRAIN_STEP). Same read as the decleg sibling: the policy learned to survive to truncation via a safe static stand (zero over_current/tilt deaths) but never completed a real forward-projecting swing, so step_event income never turned on. Architecture is not the confound (both arms converge to the identical basin/value). Closes the step-event-only pretrain mechanism at 2M for both architectures; the exploration-bootstrap problem (fresh random init never randomly stumbles into a full qualifying swing within 2M with no shaping near a partial one) is the likely root cause, not a reward-ranking defect (the bank's own ranking is correct).

