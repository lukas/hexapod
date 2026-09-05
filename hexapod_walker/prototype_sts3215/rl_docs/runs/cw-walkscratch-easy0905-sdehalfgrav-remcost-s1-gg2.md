# cw-walkscratch-easy0905-sdehalfgrav-remcost-s1-gg2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ FAIL (misaligned)

**created**: 2026-09-05T13:17:16+00:00

**pod**: hexapod-mjx-train-11

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sdehalfgrav-remcost-s1

**wandb_id**: dq6gfe29

**hypothesis**: Plain English: sdehalfgrav-remcost-s1 fixed the survival-duration exploit (falls 800->190, ep_len->1033) but still shows the LEGPARK-SKATE fingerprint (legs 1,4 permanently parked, gait_valid 0/6 every det+sto episode, contact-sheet confirms two retracted legs) -- this continuation keeps its 40M of survival+speed skill via a genuine --init-from own-checkpoint warm start (hand-built arg vector, not launch_run.py respec, to strip --use-sde/blank --activation-fn and dodge the documented SystemExit gotcha) and multiplies transport income by the MIN over support legs of a recently-completed-real-swing score (reward.walk_gait_gate=1.0, gait_gate_stride_mm=5, k_step_event=1.0 -- the same bank-proven structural fix already funded on the bare-sde recipe as sde-s1-c3gg/sde-s2-c3gg), so parked legs zero income until all six cycle. Tests whether the gait-gate repair generalizes across the sde+halfgrav+remcost recipe family, not just bare sde. (-gg name suffix retried as -gg2: original -gg names collided with an earlier self-corrected mis-launch already registered in W&B, append-only names REFUSED the retry.)

**gate**: Acquisition milestone at OWN physics (0.5g) WITH gait validity: 20s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, gait_valid true (no sacrificed legs, all six legs swing_count>5) in the majority of det episodes, six-leg lift/place on video, no belly drag; report sto. Watch env/walk_gait_gate_factor (must rise from ~0 toward 1) and env/walk_speed (must not collapse to ~0). Per 08-21: factor rising + speed alive but gate unmet at 40M = continue; reward flat AND factor flat at 0 = FAIL.

**verdict**: Result: 4th confirmation (after sde-s1-c3gg/sde-s2-c3gg/remcost-s0-gg2) that the walk_gait_gate+k_step_event structural repair does not escape LEGPARK-SKATE -- fails identically on this recipe's other seed. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_sdehalfgrav_remcost_s1_gg2_gate/report.json, 40.37M steps. 0/24 falls, gait_valid only 2/24 (walk/det 0/6, walk/sto 1/6, walk_startjitter/det 0/6, walk_startjitter/sto 1/6) -- legs chronically parked at duty_cycle 0.0-0.03 in nearly every episode. Video (walk_det_0.png contact sheet) shows the same splayed-rigid-leg signature as s0-gg2/bare-sde: two legs held stiff while the rest drag the body. env/walk_gait_gate_factor (wandb_history.csv) sits 0.985-1.0 essentially the whole run (saturated near ceiling, never a real ~0->1 climb) despite the harness flagging near-total leg sacrifice -- same rare-token-dodge root cause as every other gait-gate FAIL this campaign. Reward quarters -694.5/-530.0/-39.7/538.0 (climbing) is not evidence of progress per 08-21: the mechanism's own proxy is already saturated, so budget cannot move it further. Why: same closed mechanism (CURRENT_TRUTHS.md 09-05 ~14:3x), now 4/4 across bare-sde and sdehalfgrav+remcost recipes. Next: the walk_gait_gate/k_step_event lever is now CLOSED across every recipe tried (4/4 FAIL) -- do not relaunch it anywhere in the sde/sdehalfgrav family. Any further LEGPARK-SKATE repair needs a genuinely new per-leg-utilization pricing mechanism (hard minimum-duty/swing-count price, not a gameable completion score), with its own design+bank pass before further spend on this family.

