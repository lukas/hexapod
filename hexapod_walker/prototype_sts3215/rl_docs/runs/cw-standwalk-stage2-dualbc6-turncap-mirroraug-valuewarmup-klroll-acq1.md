# cw-standwalk-stage2-dualbc6-turncap-mirroraug-valuewarmup-klroll-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-01T00:57:40+00:00

**pod**: hexapod-mjx-train-0

**steps**: 38000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-valuewarmup-acq1

**wandb_id**: kqfwlelj

**hypothesis**: Plain English: does capping the actor's realized per-update policy jump stop the turn-authority erosion the whole campaign has chased? Identical to the just-FAILED valuewarmup-acq1 (actor frozen 8M steps, critic-only warmup -- which measurably FIXED critic credit assignment: 3/4 probe_yaw_credit CREDIT-REWARDS at the freeze boundary, first full mechanism-pass of the campaign) plus exactly ONE new mechanism: --kl-rollback=0.05 (attach_kl_rollback, built+unit-tested 08-18 in update_health.py, never used in this policy family), which snapshots the policy each update, rolls back any update whose realized approx_kl exceeds 0.05, and halves the actor LR (floored at 1%). The dig-in measured the exact failure it targets: valuewarmup's FIRST post-unfreeze update realized approx_kl 3.76 (seed1: 4.90) -- an advantage shock from 8M steps of critic-only convergence -- and the authority collapse window (pos wz_med -43% within 2M of unfreeze) coincides with it; beyond the shock, every run in this family trains at approx_kl 0.08-0.15 / clip_fraction ~0.28 steady-state despite default --target-kl 0.02, because SB3 early-stop cannot undo an already-applied minibatch. Prediction-if-true: kl_rollback fires at the unfreeze boundary (train/kl_rollback_count > 0, realized KL bounded <=0.05 after), the 10M probe_turn_authority pos read stays >=0.09 (vs parent's measured 0.063 shock dip), the critic's credit fix persists past 16M (parent: re-BLIND by 16M), and final authority holds >=0.10 both signs. Prediction-if-false: erosion proceeds at the same rate with KL bounded -- oversized realized updates are refuted as the second driver, remaining suspects are reward-scale advantage dominance / GRU-dual weight sharing (next lever: reward-decomposed multi-head critic).

**gate**: Two-stage, vs the parent's own measured 12-pt curve (logs/ckpt_eval/turn_authority_dualbc6_turncap_mirroraug_valuewarmup_acq1_*.json). MECHANISM (read at ~10-12M snapshots): PASS-mechanism if train/kl_rollback fired at/near the 8M unfreeze AND post-unfreeze realized approx_kl stays <=~0.05 AND probe_turn_authority pos wz_med at 10M >= 0.09 (parent shock dip: 0.063); FAIL-mechanism if the shock/KL profile is unchanged (guard did not engage -- fix wiring before reading further). FINAL (38M): PASS if probe_turn_authority wz_med >=0.10 both signs AND det walk gait_valid >=5/6 zero falls AND purewalk det progress_ratio in/above 0.40-0.48 -- promote to stage2 source. PARTIAL if erosion merely slows (quantify time-constant vs parent curve; if credit stays CREDIT-REWARDS past 16M but authority still decays, credit+update-size are jointly insufficient -> escalate to reward-decomposed critic). FAIL if final wz_med lands at the <0.05 floor both signs with KL provably bounded -- oversized-update driver refuted.

