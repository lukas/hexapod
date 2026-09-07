# cw-assistfade-rung4-revhandoff-noanneal-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-07T10:05:35+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-assistfade-rung4-revhandoff-s0

**wandb_id**: yj67mmvq

**hypothesis**: Plain English: the first rung-4 canary's handoff worked (episodes genuinely start mid-stride) but the policy re-settled into a static stand within a fraction of a second and never walked again for the rest of any episode -- is that because the 2.0s handoff assist gets annealed away (schedule 2.0->0.0 over steps 0.8M-1.8M, i.e. removed by 90% of the 2M canary) before PPO has anything of its own to fall back on, the same too-early-scaffold-removal failure shape rung 2's anchor lesson already named? Single-lever isolation: push the SAME schedule's t0/t1 to 1.9M/2.0M so goal.walk_reverse_handoff_s stays at its full 2.0 value for essentially the WHOLE 2M canary (anneals only in the last 100k steps, never fully removed within this budget) -- every other cfg byte-identical to the FAILED s0 (same phase-sv-contact diet, same random init, same seed). Prediction-if-true (anneal-timing was the driver): walk/det prog_ratio clears meaningfully above the FAILED s0's -0.01 (i.e. genuine sustained forward motion appears while the crutch is still up), even if it collapses again once a LATER canary anneals it away -- this run's own gate is just 'does keeping the crutch up longer let PPO discover ANY sustained gait', not the full rung-4 DONE bar. Prediction-if-false (crutch duration/scaffold isn't the driver): prog_ratio stays at the same ~0 static-stand fingerprint even with the crutch permanently up, which would point at the reward diet itself (phase-sv-contact, already independently refuted at rung 1/no-handoff) rather than the anneal schedule as the blocker -- in that case do not chase a 3rd handoff-schedule variant, escalate to a design review of the diet under handoff instead.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY (2M): do not judge mature gait. PASS if (a) trains to completion, no NaN/crash; (b) handoff engages (frame-0 video already-moving, matching s0); (c) walk/det prog_ratio clearly above s0's -0.01 fingerprint (bar: median >= 0.15, matching the walkcurr acquisition-milestone floor) OR clearly rising through training (reward/eval curve), not flat-static. FAIL-MECHANISM if prog_ratio stays in the -0.03..0.02 static-stand band with reward also flat, matching s0 exactly -- that would mean the anneal-timing lever is refuted and the phase-sv-contact diet itself is the blocker even with permanent assist.

