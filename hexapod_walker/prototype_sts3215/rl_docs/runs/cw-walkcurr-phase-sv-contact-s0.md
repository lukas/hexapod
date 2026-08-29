# cw-walkcurr-phase-sv-contact-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-29T16:39:01+00:00

**pod**: hexapod-mjx-train-2

**steps**: 20000000

**parent**: cw-walkcurr-pf-central-sv-s0-rr2

**wandb_id**: ii8bfok6

**hypothesis**: Plain English: does a SMALL alternating-tripod contact-agreement reward provide the missing gait grammar without dictating joint angles? Same clone as cw-walkcurr-phase-sv-obsonly-s0 (sv diet, seed 0, 20M, random init, phase obs at 1.333 Hz) plus reward.k_phase_contact=0.03 — Siekmann-style periodic contact composition: per tick pays k*(tripod agreement-0.5)*2, so parked/dragged legs net ~0 and only clock-synced stepping earns; runs only while a velocity is commanded. Dose 0.03 = half the freeprog income coefficient (small per directive) — recorded assumption, as is the inferred arm name (directive truncated before Arm B). Operator directive 08-29: gait clock allowed for the phase-sv line; still no BC/imitation/AMP/warm-start. WALKCURR_PHASE_SV bank green pre-launch (travel > park/stall/belly-sit by >3.0; wrong-way/topple still lose; snapshot exp/cw-walkcurr-phase-sv-wave1).

**gate**: PASS if by 20M: DR-0 walk det prog_ratio >= 0.5, gait_valid >= 4/6, zero falls, and the travel is real stepping (slip/m <= 3, not skate). FAIL on the static basin, or on the named exploit: clock-synced march-in-place (phase_agreement > 0.8 with prog_ratio < 0.2 — watch reward_phase_contact vs travel at triage). If false with reward still rising, apply the 08-21 ruling (continue/realign) before any STOP. A PASS on either phase arm queues seed replicates s1/s2 (directive hypothesis 4); comparison set: no-phase control central-sv-s0-rr2, decleg-sv wave, allheading BC-anchor line (hypothesis 5).

