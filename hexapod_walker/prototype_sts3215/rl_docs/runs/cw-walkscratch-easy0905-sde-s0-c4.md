# cw-walkscratch-easy0905-sde-s0-c4

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-05T11:11:32+00:00

**pod**: hexapod-mjx-train-8

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-base-s1

**wandb_id**: 6e15jpmw

**hypothesis**: Own-checkpoint 40M continuation of sde-s0-c1 (ACQ CONTINUE: ep_len_mean recovered from a mid-training trough to 239 by 40M, ep_rew_mean ended positive +17.1, v_along_cmd ~0.15-0.17 m/s -- same still-learning fingerprint sde-s1/s2/s3 already earned continuations for). CORRECTED relaunch of sde-s0-c3, which silently trained only 2M steps because it was respec'd --from base-s0 (that run's own config is the 2M-canary scale, steps defaulted from it) instead of a 40M-scale sibling -- this respec is --from base-s1 (a 40M full-acquisition config) WITH an explicit --steps 40000000 override so the budget cannot silently inherit wrong.

**gate**: Acquisition milestone at own easy physics: 20s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Per 08-21 ruling: FAIL only if v_along_cmd/reward_walk go flat or ep_len re-collapses without recovery; continue further if still climbing at cutoff.

**verdict**: MISALIGNED (08-21/RUN_INTERPRETATION #3: exploit-on-video with rising reward): confirms the DIG-IN trigger. W&B looked PASS-shaped (ep_rew_mean quarters 53/307/1004/1614->1781, ep_len_mean climbing to 1917/2000, no plateau) but the gate harness (24/24 episodes across walk det/sto + walk_startjitter det/sto, logs/ckpt_eval/cw_walkscratch_easy0905_sde_s0_c4_gate/report.json) shows a SACRIFICED-LEG QUADRUPED SHUFFLE, not six-leg walking: leg index 4 duty_cycle 0.00-0.03 (chronically airborne, 3-9 touches in a 20s/2000-tick episode, EVERY scenario incl. startjitter) and leg index 1 duty 0.01-0.23 (sacrificed in det, partially recovers in sto); the 4 remaining legs sit duty 0.6-0.97 with swing_count 55-143 but stride_m_mean=0.007 (7mm) -- a high-frequency micro-quiver, not real strides. Net forward_dist_m 0.54-1.44/20s (barely clears the >=0.03 m/s floor via this shuffle, not a stride) at slip_per_m 4.8-5.2 (det/sto), ~1.7-1.8x the 2.9 teacher-band ceiling. 0/24 falls (survival is real, that's why reward climbed) but the gate's own text ('six-leg lift/place on video, no belly drag') is not cleared -- hand-pulled frame strips independently showed the body pose changing only cosmetically across 11s-apart samples, consistent with the 7mm/tick stride finding. Root cause: bare easy0905 recipe (freeprog income only, k_park_duty/k_walk_idle_charge/k_loadslip_excess all 0) has NO price on a leg parked outside duty [0.1,0.9] or on near-zero joint velocity -- exactly the gap the walkcurr track's own WALKCURR_PF_IDLE_TERM bank (test_task_semantics.py, 08-24) already named+fixed on the older pf_fwd lineage ('soft park/idle prices alone leave a frozen stand as PPO's cheapest optimum; needs a qvel-based termination WITH them, not instead'). Now 3/3 full-gravity sde seeds (this run + sde-s1-c2/s2-c2, concurrent-cycle-owned) share the identical fingerprint at 40M -- class-confirmed, not seed noise. base/halfgrav (non-gSDE) families train cleanly under the SAME bare recipe (4/4 ACQ PASS, six-leg video-confirmed), so this is gSDE-exploration-specific, not a universal reward defect. Next: launched cw-walkscratch-easy0905-sde-idleterm-{s0,s1} this cycle (2M canaries, fresh-from-scratch, train-2/3, VERIFIED RUNNING) porting the exact bank-proven WALKCURR_PF_IDLE_TERM combo (k_park_duty=4/k_walk_idle_charge=2/k_loadslip_excess=4.5 + safety.walk_idle_terminate_s=3 qvel<2deg/s) onto the sde EASY_BASE recipe -- read alongside sde-s1-c2/s2-c2's own root-cause before funding further bare-sde 40M budget. Do NOT retry reward.walk_gait_gate/k_walk_move_current here without re-reading RL_LOG 08-25: both were CLOSED (made things worse) on this exact leg-sacrifice class under the joystick track's harder full-DR curriculum.

