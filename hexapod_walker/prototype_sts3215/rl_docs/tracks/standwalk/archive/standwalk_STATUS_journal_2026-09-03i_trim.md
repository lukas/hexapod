Update, 2026-09-03 ~12:1x: **item 1 CLOSED — resamplematch-mild-canary
{,-s1} CANARY FAIL - MECHANISM (PARTIAL-shaped), diet-rate family
CLOSED at both doses, both seeds; pivoting to the structural
forward+turn co-occurrence lever.** The milder dose (resample_s
5.0/jitter 0.35, down from the CANARY-FAIL hard dose 4.0/0.5) DOES fix
the falls sub-claim cleanly on both seeds: `probe_turn_authority`
wz_med 0.147-0.212 rad/s (well above the 0.07 floor, zero probe
falls); a matched `eval_checkpoint.py --modes walk --per-mode 16`
own-DR read (dr-scale 0.0/0.5 x det/sto, no-video for speed, dr0
video spot-check confirms clean six-leg gait/gait_valid=true) shows
**0/16 immediate-tilt terms in either seed's own-DR subgroup** — the
hard-dose fall mode does not reproduce; the only termination present
(1/16, both seeds identically) is a late (t~22-23s, deep in the hold
segment) `hold_min_load` term matching the same baseline own-DR noise
floor seen elsewhere (stdwalklohi-acq1 fastwalkcheck, also 1/16). But
steering/slip still do NOT clear the gate's PASS bar: `dir_err_med`
35.1-40.5deg (seed0) / 38.6-39.5deg (seed1), flat vs the hard-dose
FAIL band (38-41deg), nowhere near the required >=20% drop;
`course_err_1s_med` mixed-to-worse (seed0 own-DR 20.7-22.8 vs that
run's 9.6-12.6 FAIL band; seed1 roughly flat 7.3-11.4); `slip_per_m_med`
still breaches ~3.8 in the own-DR subgroups that matter (seed0
4.53-4.82, seed1 3.98). **Conclusion: the resample_s/jitter DIET-RATE
lever does not move steering at ANY dose tested (hard or mild, either
seed) — the earlier own-DR-fall scare was dose-linked knife-edge
instability, now resolved by the milder dose alone, not evidence the
lever helps steering.** Diet-rate family is CLOSED. Per the
pre-registered fork: pivoting to the STRUCTURAL forward+turn
co-occurrence lever — reduce `goal.walk_yaw_zero_frac`
(0.5->lower)/`goal.walk_turn_in_place_frac` (0.30->lower) so more
training episodes require simultaneous forward+turn, since
probe-confirmed turn-IN-PLACE authority is already strong (wz_med
0.15-0.22 across every arm tried so far) but forward+turn
CO-OCCURRENCE has never actually been exercised at training time —
every diet-family arm held those two fractions constant. Full verdict
text + numbers: ledger verdicts for `resamplematch-mild-canary`/`-s1`;
raw artifacts `logs/ckpt_eval/standwalk_resamplematch_mild_canary{,_s1}
_walkcheck/`, `logs/ckpt_eval/probe_turn_authority_resamplematch_mild_
canary{,_s1}.json`.

Earlier updates (item 0 close, resamplematch/turndiet-s1 diet-match
refutation, joint-frame-stamp fix, fast-read, getup/q0/hold/
joint-frame-v2 fixes, 09-02 merge-recovery) moved VERBATIM to
`archive/standwalk_STATUS_journal_2026-09-03h_trim.md` +
`2026-09-03{a..g}_trim.md` + `2026-09-02{f,h}_trim.md`.

## Next (updated 09-03 ~12:1x)

1. **Launch the structural forward+turn co-occurrence canary**: a 2M
   cheap mechanism-health canary pair (2 seeds) off the SAME
   stdwalklohi-acq1 ancestor the whole diet family used, one lever —
   lower `goal.walk_yaw_zero_frac` and/or `goal.walk_turn_in_place_frac`
   so training exposes forward-motion-while-turning far more often
   (currently 50%/30% of segments are pure-yaw-zero or pure-turn-in-
   place, i.e. forward+turn co-occurrence is comparatively rare). Gate:
   same probe_turn_authority + walk-only n=16 det/sto x dr0/ownDR
   instrument as the diet-family canaries, same PASS/PARTIAL/FAIL
   rubric, compared against the SAME resamplematch-canary FAIL numbers
   (dir_err 38-41deg/course_err_1s 9.6-12.6deg/slip~3.8) — this is the
   next and last item on the track's own pre-registered turn-authority
   fork before escalating to a full acquisition-scale reward change.
2. **Closed (archives 09-02{,b..h}, 09-03{a..h}):** update-size/
   reward/exploration/anchor/turn-skip/yaw-credit/diet/duration/
   switch-jump/frame-blend/current-confound sweeps; cap29 acquisition
   (PARTIAL); log_std anneal dose grid (`hi` PASS, `mild` FAIL); item
   0 sto/det convergence-at-scale (PASS); resamplematch/turndiet-s1 +
   resamplematch-mild-canary{,-s1} diet-match-rate hypothesis (CLOSED,
   refuted at both doses/both seeds, this update).
