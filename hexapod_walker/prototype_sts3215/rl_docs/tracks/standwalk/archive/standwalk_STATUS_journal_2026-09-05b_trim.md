# Archived standwalk STATUS banner — 2026-09-05b (verbatim)

Moved here 2026-09-05 ~04:5x when the phase-scheduled multi-teacher
mechanism (item 1) was built + tested + launched, superseding this
banner. Current STATUS.md has the fresh Update.

# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-05 ~04:0x: **mlcontprice8 literal DONE-gate read is IN
— FALL (item 1 CLOSED). Reward/architecture lever search for steering
is now EXHAUSTED (~20 arms); a new probe REFUTES the "cap is
miscalibrated" theory.** `session_verdict.json` (n=32, dr0+ownDR,
non-strict, train-9): zero falls, gait_valid 1.0, height_err 3.2mm —
clean. vs the standing best band (`cap29-stdwalklohi-acq1{,-s1}`:
dir_err 43.6-44.56deg/slip 2.819-2.939, n=128): dir_err_med 42.26deg
edges better but slip_per_m_med 3.696 is a clear regression (+26-31%,
breaches the 2.9 cap by far more than the baseline's borderline miss)
— the transtress/hold-load-price branch cost walk quality without
buying enough steering. Standing best stays `cap29-stdwalklohi-acq1
{,-s1}`, itself still short of gate. Combined with the already-closed
dose-bracket/DR-draw/steering-FAIL-wall/arch-swap/BC-anchor-turn-skip
axes (item 4), the reward+architecture lever space for steering/slip
is now **exhaustively searched** (~20 arms: yawarm/yawboost/omegaboost
/selomegaboost/combdose/combskip dose sweeps x2 seeds, log_std anneal
grid, sto/det convergence, resamplematch, `TripleGruActorCriticPolicy`
turn-core swap + `noyawcredit` control, DR-draw n=20 — all FAIL/
CLOSED; frozen `cap29-stdwalklo-hi{,-s1}` stays the reference). Also
this cycle: extended `probe_dir_floor.py` with an opt-in periodic
heading-resample mode (`--resample-s/-jitter/--heading-max-deg/
--blend-s`, default OFF=bit-exact; tests 3/3 green) to test whether
the 40deg `dir_err_cap` was calibrated against an easier static-
heading floor than the session's real 3s-resample/full-circle-heading
dynamic — **REFUTED**: teacher tick `dir_err_med` stays 8.6-9.2deg (2
seeds, 20 flips/60s) even under realistic resampling — the cap is
real/achievable, the ~42-44deg plateau is a genuine unclosed policy
gap. Evidence: `logs/ckpt_eval/..._mlcontprice8_donegate_flatonly/
session_verdict.json`; `/tmp/dirfloor_resample{,_s1}.json`. **No GPU
relaunch this cycle** — every known lever on this recipe is closed
(item 1); next step is a different mechanism CLASS (Stage 2's
pre-declared KL-to-teacher/multi-teacher), needing design+bank work.

Prior updates (09-04 ~13:2x..09-05 ~02:4x) archived verbatim in
`archive/standwalk_STATUS_journal_2026-09-0{4hh,4jj,4kk,4ll,5a}_trim.md`.

## Next (updated 09-05 ~04:0x)

1. **Design + build a teacher-distillation mechanism that is NOT
   reward-coefficient dosing on the current recipe** (Stage 2's own
   pre-declared alternative: KL-to-teacher action-distribution match,
   or phase-scheduled multi-teacher). The dose-lever axis is closed
   and the cap-miscalibration theory is refuted (see Update) — the
   ~42-44deg vs teacher's ~9deg gap is real and needs a structurally
   different lever. Scope it, bank-prove any reward-semantics touch,
   THEN launch — the track's only remaining open lever.
2. **DR-draw correlation — CLOSED.** No dominant DR field at n=20;
   k=8 is the standing ceiling dose (now also known to cost slip on
   the literal gate — do not re-promote mlcontprice8 or raise dose).
3. **Steering branch — CLOSED, both seeds, all axes** (09-04 ~17:0x
   sweep + this cycle's architecture-swap/turn-skip/cap-recalibration
   closures). No further lever acquisition; frozen parents
   (`cap29-stdwalklo-hi{,-s1}`) remain the reference. Rise-stall
   stays CLOSED.
4. **Closed** (archives 09-02{,b..h}, 09-03{a..u}, 09-04{aa,cc,dd,jj,
   kk,ll}, 09-05a): architecture-split; lever/dose/seed sweeps incl.
   `TripleGruActorCriticPolicy` turn-core swap + `noyawcredit`
   control; `bc_anchor_walk_turn_skip` (`combskip`) ablation; cap29
   acquisition (PARTIAL); log_std anneal grid; sto/det convergence;
   resamplematch; rise over_current dig-in; semantics-bank twins;
   IK-feasibility groundwork; mlcontprice2/8/16 dose bracket (k=8
   ceiling, now known to cost slip); steering FAIL-wall dig-in;
   DR-draw correlation (n=20); mlcontprice8 literal DONE-gate read
   (FALL); dir_err_cap miscalibration theory (REFUTED).
