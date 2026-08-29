# cw-walk-allheading-mlp-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CRASHED

**created**: 2026-08-29T15:39:53+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walk-allheading-mlp-scratch1

**wandb_id**: bya5fmnt

**hypothesis**: Plain English: continue the healthy matched-step MLP control twin (2M mechanism canary PASSED: bc-anchor loss falling, course-income mechanism live and recovering through the from-scratch 100Hz reward valley, no NaN/collapse, reward tracks the transformer arm closely) into a real 40M learning budget alongside its transformer sibling, so the pair stays comparable through acquisition and this arm keeps serving as the reference trajectory the gate text names it as. Prediction-if-true: course-income share keeps climbing past the valley and by 40M the balanced 8-heading eval_cmd_suite panel shows every heading moving at >=half the teacher's own completion (>=0.19) with zero falls -- and the MLP either matches or falls behind the transformer, telling us whether the extra architecture capacity actually helps this task. Prediction-if-false: course-income share stays pinned near the canary's trough -- BC-anchor imitation dominates over command-following at this budget too, confirming the problem is reward composition, not architecture. Strongest alternative: 40M still is not enough to fully exit the valley (08-24 FACT: this exact sibling crossed zero reward only at 12-14M in the prior architecture-canary precedent) -- judge interim checkpoints on trend, never absolute value.

**gate**: 40M acquisition, same gate as the transformer twin: eval_cmd_suite balanced-heading panel, 8 headings x 0.08 m/s + stop, det+sto -- EVERY heading must move (completion >=0.19, half the teacher's measured 0.373-0.385) with zero falls; lateral/reverse weakness = not passed.

**verdict**: INFRA CRASH, not a science verdict -- pod hexapod-mjx-train-1 was OOMKilled (kubectl describe: 'State Terminated, Reason OOMKilled, Exit Code 137' at 2026-08-29T16:23:08Z, container mem limit 96Gi) partway through the 40M acquisition budget at 17,547,264 steps (~44%, ~41 min wall clock at ~7000fps). Training itself looked healthy and unremarkable up to the crash: train/bc_anchor_loss_walk stayed low/flat (~0.0002-0.0003, no drift) the whole run; terminations/over_current stayed single-digit after the shared ~800k-1.05M transient bump documented in the canary verdict; ep_rew_mean was noisy but not degenerating (peaks 250-440 around 5-13M, a dip to -28..35 around 13.7-14.7M, partial recovery to 180-210 by 15.7-17.5M -- ordinary PPO noise, no NaN, no collapse); env/walk_course_income_support drifted down from its canary-era 0.7-0.9 into a noisier 0.03-0.33 band with no clear monotonic direction -- inconclusive on its own, would have needed the full 40M to read honestly. Sibling cw-walk-allheading-tf-acq1 (same node g131eec, same recipe family, transformer variant) is unaffected and past 21M steps, so this is not a node-wide memory-pressure event -- looks localized to this run/pod. Root cause UNDETERMINED (no crash log recoverable: hexapod-mjx-train-1 is Failed/un-execable, kubectl exec and kubectl cp both refuse 'cannot exec into a container in a completed pod'; no PVC backs these pods -- train_ppo_mjx.py's periodic checkpoint/W&B artifact never made it to controller storage before the OOM, so the 17.5M-step checkpoint is UNRECOVERABLE, unlike a normal finish where the watcher prestages it). Per the DEAD-pod checkup protocol (clean up + retry once): relaunching from the last recoverable checkpoint (the scratch1 canary, since acq1's own checkpoint never synced) as cw-walk-allheading-mlp-acq1-rr1 on a fresh healthy pod (train-3), same hypothesis/gate/budget as the original acq1 launch -- this re-spends ~18M steps of budget but preserves the tf/mlp matched-step comparison the standwalk track's canary gate is built on. Also recreating hexapod-mjx-train-1 (delete+apply+bootstrap) since it cannot host any run in its current Failed state; if a retry OOMs again on a freshly-recreated pod, escalate as a real memory-leak defect (2 recreated-pod deaths would rule out '13-day pod accumulated-state' as the explanation).

