# cw-walkscratch-easy0905-sde-s1-c3gg

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ FAIL

**created**: 2026-09-05T12:40:56+00:00

**pod**: hexapod-mjx-train-4

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s1-c2

**wandb_id**: zr5lg756

**hypothesis**: Plain English: sde-s1-c2 learned to survive by parking 1-2 legs and skating the rest (LEGPARK-SKATE, ACQ FAIL misaligned) — this continuation keeps its 40M of survival skill but multiplies ALL transport income by the MIN over support legs of a recently-completed-real-swing score (reward.walk_gait_gate=1.0, the structural 08-13 close of the leg-sacrifice loophole that additive k_park_duty pricing cannot close), so the parked legs zero the income until all six cycle; gait_gate_stride_mm=5 lets the current ~6mm active-leg swings qualify (the MIN is held at 0 by the PARKED legs regardless of bar, so this only speeds income recovery once all six move), and k_step_event=1.0 pays each completed forward swing per-leg = the direct gradient for waking legs 1/4. Semantics-bank gait-gate trio repaired and 4/4 green this cycle (snapshot exp/walkcurr-legpark-skate-digin-gaitgate-bank-repair) before this launch.

**gate**: Acquisition milestone at easy physics WITH gait validity: 20s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, gait_valid true (no sacrificed_legs, all six legs' swing_count > 5) in the majority of det episodes, six-leg lift/place on video, no belly drag; report sto. Watch env/walk_gait_gate_factor (must rise from ~0 toward 1) and env/walk_speed (must NOT collapse to ~0 — full-park recapture = FAIL regardless of reward). Per 08-21: factor rising + speed alive but gate unmet at 40M = continue; reward flat AND factor flat at 0 = FAIL (income blackout, retry at lower gate dose e.g. 0.7).

**verdict**: FAIL (misaligned) - the structural walk_gait_gate+k_step_event repair does NOT escape LEGPARK-SKATE. Harness: 1/24 gait_valid (walk/det 0/6, walk/sto 0/6, walk_startjitter/det 0/6, walk_startjitter/sto 1/6), leg 4 chronically parked (duty 0.0, swing_count 3/20s) in every walk/walk_startjitter det scenario; leg 1 (the OTHER sde-s1-c2 sacrificed leg) is now active (duty 0.34-0.96) so the repair did wake ONE of the two originally-parked legs, not both. 0/24 falls, walk_speed stable 0.13-0.17 m/s (not declining like the pre-repair parent), ep_len saturates 2000/2000, ep_rew_mean still climbing gently to 2688 at 40M cutoff (quarters 1436/2477/2616/2687-ish, no plateau). Root cause of the repair's failure, read directly from wandb_history.csv: env/walk_gait_gate_factor sits at 0.98-0.99 for the ENTIRE second half of training even though the harness confirms leg 4 at duty 0.0 - the reward-side gate's 'recently completed swing' scoring window accepts leg 4's rare 3-swings-per-20s as enough to keep the MIN-over-legs factor near 1, so it never actually zeros income the way the harness's stricter duty>0.10 bar requires. This is a threshold/window mismatch, not a still-training case: reward and harness diverge with reward's own internal proxy (the gate factor) ALSO plateaued high, not rising toward the true fix. Contact sheet (logs/ckpt_eval/cw_walkscratch_easy0905_sde_s1_c3gg_gate/contact_sheet.png) shows one leg held rigid/extended while the body barely translates - visually consistent. Per 08-21 this is the MISALIGNED branch: the gate mechanism itself needs a stricter minimum-swing-count/duty term, not just a completed-swing score, before it can be trusted to price a rare-token dodge. Cross-confirmed by an independent seed (sde-s2-c3gg, verdicted separately, same failure signature).

