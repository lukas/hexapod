# cw-walkcurr-sac-sv-s1-cont1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: LAUNCH_CRASH

**created**: 2026-08-29T18:29:43+00:00

**pod**: hexapod-mjx-train-5

**steps**: 10000000

**parent**: cw-walkcurr-sac-sv-s1

**hypothesis**: Plain English: SAC seed-1's 2M-step discovery run learned a real stepping gait (all 6 legs cycling, speed matching the 0.05-0.06 cmd band) but falls over via tilt_pitch/tilt_roll in every single eval episode within a couple of steps (fwd 0.02-0.05m) -- a stumble/balance problem, not the stuck-in-place static-quiver problem every PPO arm had. Continuing training on the IDENTICAL SV diet (freeprog income + term_penalty=24, no explicit roll/pitch pricing) from this exact checkpoint tests whether more steps let SAC's own max-ent exploration + the existing term_penalty teach fall-avoidance now that stepping itself is no longer the bottleneck (08-21 ruling: bad full-gate eval + a live, non-collapsing training signal = continue, not FAIL). Only lever: 5x budget (2M->10M), same algorithm/diet/seed/checkpoint. Prediction-if-true: env/walk_speed holds in the 0.05-0.08 m/s band while roll_peak_deg / fall rate on the rung-1 panel drops and forward_dist_m rises past the current ~0.02-0.05m ceiling. Prediction-if-false: falls persist at the same rate/roll_peak with speed pinned -- the diet has no balance-shaping signal strong enough for this lever alone, and the next fork is adding a mild anti-tilt price (still SV-diet-legal, a magnitude question not a mechanism-bank question since roll/pitch pricing already exists in REWARD.md, just zeroed here) rather than more raw budget.

**gate**: Rung-1 C-env det+sto fixed-forward panel (n>=6 each) at 10M: PASS needs progress_ratio med >=0.35, slip/m <=3.0, gait_valid >=4/6, and falls (tilt_pitch/tilt_roll term) on <=1/6 det episodes -- i.e. the stumble is fixed, not just the stepping. PARTIAL/continue (08-21): fall rate or forward_dist improving vs this run's baseline (24/24 falls, fwd med ~0.03m) even short of the full bar. FAIL: fall rate and forward_dist unchanged (still ~24/24 falls, fwd ~0.02-0.05m) at 10M with flat reward -- diet lacks a balance-shaping signal, fork to an anti-tilt pricing dose next.

**verdict**: Not a science result -- launch-config error, never trained a step. Pod log (kubectl exec hexapod-mjx-train-5, /tmp/train_cw-walkcurr-sac-sv-s1-cont1.log): process hit train_ppo_mjx.py's --activation-fn/--init-from guard and exited before a single env step. wandb run flojqokf state=finished with an EMPTY summary (zero logged steps) confirms no training occurred. ROOT CAUSE IS DEEPER than that one flag: train_ppo_mjx.py's --algo sac path unconditionally refuses --init-from for ANY reason (stock-SB3-SAC-only restriction, see the _sac_bad check a few lines below the activation-fn guard) -- dropping --activation-fn alone would have hit that second, unconditional refusal immediately after. Checkpoint-continuation of a SAC run is not supported by this codebase at all today. No relaunch from this agent: the concurrent cycle independently reached the same root cause and already relaunched the underlying hypothesis correctly as a full from-scratch rerun at the 10M budget (cw-walkcurr-sac-sv-s1-budget10m, VERIFIED RUNNING train-5) rather than a checkpoint warm-start, since none is possible for --algo sac.

**failed_reason**: run never appeared as 'running' in W&B within 240s

