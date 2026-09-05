# cw-walkscratch-easy0905-sdehalfgrav-remcost-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CONTINUE

**created**: 2026-09-05T10:52:26+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sdehalfgrav-s0

**wandb_id**: 6zujo47q

**hypothesis**: Plain English: second seed of the survival-duration pricing fix - the sde+halfgrav cell learned to sprint ~0.7s and belly-flop because dying costs 10x less than the sprint pays; charging early death in proportion to forfeited survival time should make the same recipe stay up and walk. Identical to cw-walkscratch-easy0905-sdehalfgrav-remcost-s0 except --seed 11 (the failing cell showed 2/4 seed-level divergence, so the fix needs n=2 to read). Fix keys reward.term_cost_per_remaining_s=100 + term_cost_max=450, bank-proven (test_walkscratch_easy_pilot.py 17/17; sprint_fall twin +64.7 vs park +0.2 at flat 24, -385.3 under fix, survivors bit-exact). Prediction-if-true: ep_len_mean climbs toward 500-tick truncation with sustained v_along_cmd. Prediction-if-false: park-recapture (ep_len ~500, walk_speed ~0) = exploration problem, not pricing; stop funding the cell.

**gate**: Acquisition milestone at OWN physics (0.5g): 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Secondary (fix-specific): ep_len_mean escapes the 65-84-tick plateau. Not met with signals rising = continue/realign per 08-21; FAIL on park-recapture (ep_len ~500 with walk_speed ~0 and flat reward) or flat everything.

**verdict**: ACQ CONTINUE, not PASS/FAIL: the term_cost_per_remaining_s=100/term_cost_max=450 survival-duration fix worked on its target failure mode -- 0/12 det falls (walk/det + walk_startjitter/det), forward_dist_m med 2.17-2.60m/20s (0.11-0.13 m/s, clears the >=0.03 m/s bar), ep_len_mean climbed 110->1088 ticks across training with no plateau (escapes the pre-fix 65-84-tick fingerprint cleanly). BUT a new pathology blocks the six-leg-validity bar: legs [1,4] show duty_cycle=0.0/swing_count~2 in EVERY one of the 12 det episodes (walk/det AND walk_startjitter/det) -- not minor underuse, a fully idle prop-leg pair -- so gait_valid=False 12/12; it is walking on 4 legs with 2 held rigid, not six-leg cycling ('a walk without all six feet cycling is not walking'). Also fragile: BOTH stochastic scenarios (walk/sto, walk_startjitter/sto) fall 6/6 via tilt_roll/tilt_pitch with near-zero forward distance (0.14-0.65m) -- the deterministic policy has no margin against action noise. Sibling cw-walkscratch-easy0905-sdehalfgrav-remcost-s0 (concurrent cycle, unverdicted) shows the IDENTICAL fingerprint (legs [1,4] sacrificed det, [0,2] sacrificed sto, 0/12 gait_valid, 6/6 sto falls) with even better fwd (3.3-4.0m) -- this is a reproducible recipe fingerprint, not seed noise. Per 08-21: not park-recapture, not flat -- the fix is confirmed on survival duration but the cell needs another lever (per-leg utilization pricing, e.g. a small k_park_duty-style per-leg-swing floor) before it can pass six-leg-validity; do not fund more bare remcost seeds at this recipe, the 2-seed fingerprint is already n=2 confirmed. DIG-IN candidate for whoever decides the cell's next move (extend with a leg-utilization term vs redesign).

