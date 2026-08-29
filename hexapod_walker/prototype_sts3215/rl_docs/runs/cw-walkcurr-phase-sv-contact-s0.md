# cw-walkcurr-phase-sv-contact-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-08-29T16:39:01+00:00

**pod**: hexapod-mjx-train-2

**steps**: 20000000

**parent**: cw-walkcurr-pf-central-sv-s0-rr2

**wandb_id**: ii8bfok6

**hypothesis**: Plain English: does a SMALL alternating-tripod contact-agreement reward provide the missing gait grammar without dictating joint angles? Same clone as cw-walkcurr-phase-sv-obsonly-s0 (sv diet, seed 0, 20M, random init, phase obs at 1.333 Hz) plus reward.k_phase_contact=0.03 — Siekmann-style periodic contact composition: per tick pays k*(tripod agreement-0.5)*2, so parked/dragged legs net ~0 and only clock-synced stepping earns; runs only while a velocity is commanded. Dose 0.03 = half the freeprog income coefficient (small per directive) — recorded assumption, as is the inferred arm name (directive truncated before Arm B). Operator directive 08-29: gait clock allowed for the phase-sv line; still no BC/imitation/AMP/warm-start. WALKCURR_PHASE_SV bank green pre-launch (travel > park/stall/belly-sit by >3.0; wrong-way/topple still lose; snapshot exp/cw-walkcurr-phase-sv-wave1).

**gate**: PASS if by 20M: DR-0 walk det prog_ratio >= 0.5, gait_valid >= 4/6, zero falls, and the travel is real stepping (slip/m <= 3, not skate). FAIL on the static basin, or on the named exploit: clock-synced march-in-place (phase_agreement > 0.8 with prog_ratio < 0.2 — watch reward_phase_contact vs travel at triage). If false with reward still rising, apply the 08-21 ruling (continue/realign) before any STOP. A PASS on either phase arm queues seed replicates s1/s2 (directive hypothesis 4); comparison set: no-phase control central-sv-s0-rr2, decleg-sv wave, allheading BC-anchor line (hypothesis 5).

**verdict**: Phase-contact income (k_phase_contact=0.03, phase_obs at 1.333Hz) did NOT unlock walking -- FAIL (aligned), matches the sibling decleg-sv-s0-rr3 static/over_current signature almost exactly. Evidence: full 20M budget; env/phase_agreement sat at 0.50-0.52 (chance-level tripod agreement) the ENTIRE run, never trending toward the >0.8 exploit band OR toward genuine alternation -- the contact term is netting ~0 (reward_phase_contact ~0.0002-0.001/step) because legs aren't alternating, so it never got a chance to shape gait. ep_rew_mean quarters [194.6,183.0,169.4,167.7] peaked early then went FLAT/DOWN for the back half (not rising) while terminations/over_current climbed from 0 to 300-700/window over training -- behavior got worse, not better, on the metric that matters, so this is not a 08-21 continue case. DR-0 gate: walk/det 6/6 TERM over_current, prog_ratio med 0.13 (gate needs >=0.5), slip/m med 5.55 (cap 3.0), gait_valid 0/6 (needs >=4/6), 1-3 legs sacrificed per episode. walk/sto slightly less bad (gait_valid 5/6, prog med 0.05) but still 6/6 over_current terms and prog far below gate. Contact-sheet/det video: frozen splayed crouch, no visible translation, identical to the 15+ previously-refuted static-basin arms. Why: a small phase-agreement bonus alone doesn't force legs off the ground when the underlying freeprog/velocity income still can't escape the static basin at this budget -- same root blocker as the centralized/decleg waves, phase obs+small bonus is not sufficient by itself. Next: sibling -obsonly-s0 (phase obs, no contact bonus) and the concurrent-cycle decleg-sv/central-sv-s0-rr2 reads complete the phase-sv wave 2x2; if all arms stay pinned, escalate to the operator-named fallback ladder (SAC probe or Heess-style terrain diversity) per walkcurr STATUS Next list rather than another phase-dose variant.

