# cw-walkscratch-easy0905-sdehalfgrav-remcost-s0-gg2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ FAIL (misaligned)

**created**: 2026-09-05T13:18:33+00:00

**pod**: hexapod-mjx-train-10

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sdehalfgrav-remcost-s0

**wandb_id**: wrc80ii4

**hypothesis**: Plain English: sdehalfgrav-remcost-s0 fixed the survival-duration exploit (falls 800->190, ep_len->1033) but still shows the LEGPARK-SKATE fingerprint (legs 1,4 permanently parked, gait_valid 0/6 every det+sto episode, contact-sheet confirms two retracted legs) -- this continuation keeps its 40M of survival+speed skill via a genuine --init-from own-checkpoint warm start (hand-built arg vector, not launch_run.py respec, to strip --use-sde/blank --activation-fn and dodge the documented SystemExit gotcha) and multiplies transport income by the MIN over support legs of a recently-completed-real-swing score (reward.walk_gait_gate=1.0, gait_gate_stride_mm=5, k_step_event=1.0 -- the same bank-proven structural fix already funded on the bare-sde recipe as sde-s1-c3gg/sde-s2-c3gg), so parked legs zero income until all six cycle. Tests whether the gait-gate repair generalizes across the sde+halfgrav+remcost recipe family, not just bare sde. (-gg name suffix retried as -gg2: original -gg names collided with an earlier self-corrected mis-launch already registered in W&B, append-only names REFUSED the retry.)

**gate**: Acquisition milestone at OWN physics (0.5g) WITH gait validity: 20s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, gait_valid true (no sacrificed legs, all six legs swing_count>5) in the majority of det episodes, six-leg lift/place on video, no belly drag; report sto. Watch env/walk_gait_gate_factor (must rise from ~0 toward 1) and env/walk_speed (must not collapse to ~0). Per 08-21: factor rising + speed alive but gate unmet at 40M = continue; reward flat AND factor flat at 0 = FAIL.

**verdict**: Result: the walk_gait_gate+k_step_event structural repair does NOT generalize to the sdehalfgrav+remcost recipe -- a 3rd confirmation (after sde-s1-c3gg/sde-s2-c3gg) of the SAME rare-token-dodge misalignment on a different recipe family. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_sdehalfgrav_remcost_s0_gg2_gate/report.json, 40.37M steps. 0/24 falls, but gait_valid only 2/24 (walk/det 0/6, walk/sto 2/6, walk_startjitter/det 0/6, walk_startjitter/sto 0/6) -- legs 1 and 4 chronically parked, duty_cycle 0.0-0.03 in nearly every episode (vs 0.77-0.89 for the four active legs), swing_count single digits vs 100+ for active legs. Video (walk_det_0.png contact sheet) shows the identical splayed-rigid-leg LEGPARK-SKATE signature already seen on the bare-sde gait-gate FAILs: two legs held stiff/extended while the other four drag the body forward. Root cause confirmed identical to the closed lever: env/walk_gait_gate_factor (wandb_history.csv) is PINNED at 0.9996-1.0 for essentially the entire 40M run (not rising from ~0, not flat at 0 either -- already SATURATED near its ceiling from early training) even though the harness's duty>0.10 bar flags 2 legs sacrificed almost every episode -- the reward-side gate's completion-window scoring is satisfied by rare token swings and never prices the true duty-cycle deficit. Reward quarters -539.9/-240.3/361.1/991.9 (climbing) is NOT evidence of real progress per 08-21: the mechanism's own internal proxy is already at its ceiling, so more budget cannot move a factor that already reads 1.0. Why: this is the SAME closed mechanism (CURRENT_TRUTHS.md 09-05 ~14:3x) tested on the remcost recipe instead of bare sde -- it fails the same way. Next: closes the gait-gate repair lever at 3/3 (bare sde x2, remcost x1; s1-gg2 below is the 4th); do NOT relaunch walk_gait_gate/k_step_event on any sde/sdehalfgrav-family recipe. Any further LEGPARK-SKATE repair on this family needs a genuinely new per-leg-utilization pricing mechanism (hard minimum-duty/swing-count price, not a gameable completion score), its own design+bank pass first.

