# cw-walkscratch-easy0905-sdehalfgrav-remcost-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T10:52:26+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sdehalfgrav-s0

**wandb_id**: 6zujo47q

**hypothesis**: Plain English: second seed of the survival-duration pricing fix - the sde+halfgrav cell learned to sprint ~0.7s and belly-flop because dying costs 10x less than the sprint pays; charging early death in proportion to forfeited survival time should make the same recipe stay up and walk. Identical to cw-walkscratch-easy0905-sdehalfgrav-remcost-s0 except --seed 11 (the failing cell showed 2/4 seed-level divergence, so the fix needs n=2 to read). Fix keys reward.term_cost_per_remaining_s=100 + term_cost_max=450, bank-proven (test_walkscratch_easy_pilot.py 17/17; sprint_fall twin +64.7 vs park +0.2 at flat 24, -385.3 under fix, survivors bit-exact). Prediction-if-true: ep_len_mean climbs toward 500-tick truncation with sustained v_along_cmd. Prediction-if-false: park-recapture (ep_len ~500, walk_speed ~0) = exploration problem, not pricing; stop funding the cell.

**gate**: Acquisition milestone at OWN physics (0.5g): 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Secondary (fix-specific): ep_len_mean escapes the 65-84-tick plateau. Not met with signals rising = continue/realign per 08-21; FAIL on park-recapture (ep_len ~500 with walk_speed ~0 and flat reward) or flat everything.

