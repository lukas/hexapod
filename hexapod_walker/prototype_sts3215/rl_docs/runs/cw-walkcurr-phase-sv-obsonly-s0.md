# cw-walkcurr-phase-sv-obsonly-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-29T16:36:53+00:00

**pod**: hexapod-mjx-train-6

**steps**: 20000000

**parent**: cw-walkcurr-pf-central-sv-s0-rr2

**wandb_id**: fzunw5v5

**hypothesis**: Plain English: does merely SEEING a 2-dim tripod gait clock (sin/cos at 1.333 Hz appended to obs, no reward change) unlock from-scratch walking discovery where the blank centralized policy froze? Exact respec clone of the no-phase control cw-walkcurr-pf-central-sv-s0-rr2 (same sv diet, seed 0, 20M, mesh/100Hz, 128-64-32 tanh MLP, random init) with only the phase obs appended; k_phase_contact=0. Operator directive 08-29: gait clock ALLOWED for the phase-sv line (rule (a) superseded here; not prior-free) — still no BC anchor, no imitation loss, no AMP prior, no warm-start, actor outputs 18 joint targets. Recorded operator-sanctioned assumptions: lightweight pre-registration (single hypothesis+gate per run, no decision tree); control REUSED (parity by clone construction, no nophase-s0 duplicate); Arm B + seed-replicate-on-positive inferred from truncated directive.

**gate**: PASS if by 20M the DR-0 walk gate shows genuine commanded travel (walk det prog_ratio >= 0.5, gait_valid >= 4/6, zero falls) or clearly beats the matched no-phase control cw-walkcurr-pf-central-sv-s0-rr2 endpoint on the same read. FAIL if it lands in the static/park basin (aligned: reward and eval flat) like the 15 refuted non-clock classes. If false: phase observation alone is insufficient — the informative read shifts to the contact-reward arm; apply the 08-21 ruling before any STOP if reward is still rising.

