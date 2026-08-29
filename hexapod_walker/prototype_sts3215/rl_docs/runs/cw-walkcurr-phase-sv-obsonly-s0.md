# cw-walkcurr-phase-sv-obsonly-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-08-29T16:36:53+00:00

**pod**: hexapod-mjx-train-6

**steps**: 20000000

**parent**: cw-walkcurr-pf-central-sv-s0-rr2

**wandb_id**: fzunw5v5

**hypothesis**: Plain English: does merely SEEING a 2-dim tripod gait clock (sin/cos at 1.333 Hz appended to obs, no reward change) unlock from-scratch walking discovery where the blank centralized policy froze? Exact respec clone of the no-phase control cw-walkcurr-pf-central-sv-s0-rr2 (same sv diet, seed 0, 20M, mesh/100Hz, 128-64-32 tanh MLP, random init) with only the phase obs appended; k_phase_contact=0. Operator directive 08-29: gait clock ALLOWED for the phase-sv line (rule (a) superseded here; not prior-free) — still no BC anchor, no imitation loss, no AMP prior, no warm-start, actor outputs 18 joint targets. Recorded operator-sanctioned assumptions: lightweight pre-registration (single hypothesis+gate per run, no decision tree); control REUSED (parity by clone construction, no nophase-s0 duplicate); Arm B + seed-replicate-on-positive inferred from truncated directive.

**gate**: PASS if by 20M the DR-0 walk gate shows genuine commanded travel (walk det prog_ratio >= 0.5, gait_valid >= 4/6, zero falls) or clearly beats the matched no-phase control cw-walkcurr-pf-central-sv-s0-rr2 endpoint on the same read. FAIL if it lands in the static/park basin (aligned: reward and eval flat) like the 15 refuted non-clock classes. If false: phase observation alone is insufficient — the informative read shifts to the contact-reward arm; apply the 08-21 ruling before any STOP if reward is still rising.

**verdict**: Phase observation ALONE (walk_phase_obs=1 @ 1.333Hz, no contact bonus, otherwise identical clone of central-sv-s0-rr2) does NOT unlock walking -- FAIL (aligned), and the pathology is actually WORSE than its contact-bonus sibling: det gate slip/m med 31.79 (cap 3.0, ~6x worse than contact-s0's already-bad 5.55), prog_ratio med -0.01 (net BACKWARD/no progress, not just slow), gait_valid 0/6, legs [4,5] sacrificed in all 6/6 det episodes, fwd 0.13m/25s -- a skate/drag pathology (huge slip for near-zero net displacement) rather than contact-s0's static-quiver-to-over_current pattern, though sto mode still shows 5/6 over_current terms. Video/contact-sheet: frozen splayed crouch, no visible translation, identical basin signature to every other refuted arm. env/walk_freeprog_score sat in [-0.045,-0.017] the ENTIRE 20M run with no drift toward 0 at all (flatter than contact-s0's mild -0.033->-0.005 creep); rollout/ep_rew_mean peaked early (~201) then declined to 170.3 by the back half (quarters [194.5,186.2,177.8,172.2]) while terminations/over_current oscillated up into the 200-300/window range -- reward falling, not rising: a genuine aligned FAIL per 08-21, not a continue case. This CLOSES the phase-sv wave 2/2 FAIL (both obsonly and contact), matching the decleg-sv/central-sv-s0 wave's 4/4 FAIL already recorded by the concurrent cycle -- the full 6-arm 08-29 escalation wave (decentralized architecture x3 + centralized control + phase-obs x2) is now closed, every arm pinned in the static/skate basin with aligned (non-rising) reward. Per walkcurr STATUS Next item 2, this fires the operator-named fallback ladder: (a) off-policy SAC probe -- already being built by a concurrent cycle (train_ppo_mjx.py --algo sac, gru_policy.py SAC-checkpoint loader, uncommitted WIP observed this cycle, left untouched to avoid duplicating/colliding with it); (b) Heess-style terrain/environment diversity as a second-line fallback if SAC also fails. No new arm launched by this cycle for that reason -- avoiding duplicate SAC-fallback effort was judged higher-value than building the out-of-order (b) lever early.

