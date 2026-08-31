# cw-standwalk-stage2-dualbc4-walkteach-anchor14coef1-acq8m-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-08-30T21:21:16+00:00

**pod**: hexapod-mjx-train-3

**steps**: 8000000

**parent**: cw-standwalk-stage2-dualbc4-walkteach-anchor14coef1-canary-s1

**wandb_id**: t8tnn8ag

**hypothesis**: Seed-1 twin of the dualbc4-walkteach anchor14coef1 acq8m continuation (see seed0's ledger hypothesis for full rationale) -- same canary-checkpoint warm-start, same cfg, paired seed for replication.

**gate**: ACQUISITION (own-scope): det walk gait_valid stays >=5/6, sacrificed legs stay 0, progress_ratio improves or holds vs the canary's 0.44-0.46 (not regresses), slip/m stays inside teacher band (<=2.9), course_err_1s_med does not regress below walkteach-acq12m's own band, zero new walk terminations. Full DONE-gate mixedsession read follows per dualbc3 convention before any further unified-policy budget.

**verdict**: The 8M unified-policy continuation made the walk slower and slippier while its rising reward curve came almost entirely from the other 70% of the goal mix - it fails its own acquisition gate on the progress clause. Evidence (clean pure-walk det read, n=8+8 jitter, pod mesh-twin, gate cfg with mode_seq OFF - logs/ckpt_eval/..._acq8m_s1_purewalk_det): progress_ratio med 0.373/0.379 vs parent canary-s1 gate 0.463/0.469 (every episode 0.33-0.41, below the parent's min 0.42 - outside noise); slip/m med 2.83 (walk) / 3.14 (startjitter) vs parent 1.77/1.68, straddling the <=2.9 band; course_err_1s actually IMPROVED 5.7->3.4 deg; gait_valid 8/8, sacrificed legs 0, zero terminations - no catastrophe, a real but partial trade. IMPORTANT tooling correction: the prior triage fastcheck (prog 0.36, slip 4.4) inherited the run's own goal.mode_seq=0.75, composing walk->lower->rise segments into 'walk' episodes AND ran full_mesh vs the parent's pod twin - it overstated the slip regression ~2.5x; the mode_seq trap is now recorded in the track STATUS. Root cause chain (rising reward + regressed eval, 08-21 ruling applied): pooled ep_rew rose -100->705 but the walk-specific channels did NOT (env/reward_walk fell 0.54->0.27-0.37, walk_prog_factor flat ~0.12, loadslip_ratio 3.3->4.6-5.4) while rise/lower/hold incomes grew strongly (reward_rise_ref 0.66->0.91, rise_finish ->0.75) - the pooled scalar masked a walk<->stance trade PPO made because walk is only 30% of episodes and slip is priced only above loadslip_ok=3.0. BC walk anchor loss meanwhile MINIMIZED (0.0011->0.0003), proving state-aligned action anchoring does not preserve closed-loop gait quality. NOT a continue case: more budget feeds the same non-walk gradient. Next (launched this cycle): walk-heavy rebalance pair cw-standwalk-stage2-dualbc4-walkteach-walkheavy-acq8m{,-s1} - same init/cfg, goal-mix walk=0.60,rise=0.20,lower=0.10,hold=0.10 - gated on pure-walk prog holding >=0.44 with rise/lower retention. Hardware-ready: no (walk too slow/slippy for the joystick band, though stable and directionally obedient).

