# cw-assistfade-rung1-bcinit-taskonly-s2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY_PASS

**created**: 2026-09-06T03:28:56+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-assistfade-rung1-bcinit-taskonly-s1

**wandb_id**: 9yk9b2lr

**hypothesis**: Plain English: one of the two rung-1 seeds (s0) saw its training reward collapse in the final quarter while the other (s1) stayed healthy -- a third seed of the byte-identical recipe tells us whether task-only PPO from BC init is seed-stable at this rung or s0 is an outlier, before more acquisition budget is committed. Fresh seed-2 clone of cw-assistfade-rung1-bcinit-taskonly-s1 (same bc1_std25 init via its cloned --init-from, NOT init-from-source; rung-1 EASIER_WALKING_CURRICULUM recipe: no BC anchor, fixed forward 0.06 m/s, 10s eps, mesh/100Hz, std anneal to -3.0), 2M mechanism-health canary. Prediction-if-true (recipe stable): gait_valid clean, 0 falls, six legs, prog in s1's 0.16-0.25 band. Prediction-if-false: gait destroyed or reward collapse like s0's Q4 => rung-1 seed instability is real and feeds the joint retreat read.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (2M): do not judge skill acquisition or require the mature ignition bar. Judged JOINTLY with s0/s1 for the rung-1 read: det held-out video/eval on own cfg -- sustained forward translation, repeated alternating support transitions, all six legs participating, ZERO falls and ZERO safety terminations; progress_ratio RECORDED vs the 0.35 ignition bar but not required at 2M (s1 canary baseline 0.22); slip/current recorded. Gait destroyed or frozen/parked => counts toward the doc's retreat branch (rung 2 slower fade / rung 3 residuals). Healthy-but-slow => continuation like s1-cont8m is the sanctioned follow-up.

**verdict**: CANARY PASS (mechanism health). Third seed of the rung-1 task-only walking canary is mechanism-healthy but slow, matching seed s1 almost exactly. gait_valid 23/24 (walk/det 6/6, walk/sto 6/6, startjitter/det 6/6), zero falls, sac=[] everywhere except one startjitter/sto episode with an over_current term (uncalibrated sim current per CURRENT_TRUTHS 09-04 -- reported, not gated; single sto episode, not corroborated stall). Video strip: upright, level body, all six legs cycling, slow real forward translation. det prog med 0.23 vs the 0.35 ignition bar (s1 was 0.22; bar is recorded-not-required at 2M per gate). Joint rung-1 read now 2/3 seeds mechanism-healthy (s1, s2) vs s0 gait-destroyed -- s0 reads seed-sensitive, not recipe-level. Per the gate's healthy-but-slow branch the sanctioned follow-up is a budget continuation like s1-cont8m; launching s2-cont8m this cycle as the n=2 continuation arm.

