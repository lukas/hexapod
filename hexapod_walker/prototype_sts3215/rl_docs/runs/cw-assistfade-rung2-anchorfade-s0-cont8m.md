# cw-assistfade-rung2-anchorfade-s0-cont8m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ FAIL - INFORMATIVE (assay deadlock root-caused)

**created**: 2026-09-06T11:25:26+00:00

**pod**: hexapod-mjx-train-8

**steps**: 8000000

**parent**: cw-assistfade-rung2-anchorfade-s0

**wandb_id**: 71d7y3v2

**hypothesis**: Rung-2 anchor-fade-from-random-weights (seed 0) already clears the ignition bar at 2M under the strong anchor (prog 0.36-0.52, gv 24/24, 0 falls) but the in-training anneal-gate assay never latched (early_term_rate 0.25 in n=8 samples). More steps give the periodic assay (every 500k) many more chances to hit a clean batch, latch ignition_gate_pass, and drive bc_anchor_coef through its 4M-step anneal to 0 -- the doc's real downstream gate is deterministic held-out behavior WITH the anchor at/near zero, not under it.

**gate**: ACQUISITION continuation (8M new steps, 10M cumulative), not a fresh canary. PASS/CONTINUE if: (a) bc_anchor_anneal/gate_pass latches at least once and bc_anchor_anneal/coef visibly ramps down in wandb_history, AND (b) the held-out det+sto gate eval post-anneal still clears the ignition bar (gait_valid, 0 falls, progress_ratio>=0.35 across all 4 modes) with the anchor at/near zero. CONTINUE (not fail) if the anchor has still not annealed by 10M cumulative but reward/progress keep climbing and gait stays intact (rung1's own bcinit-taskonly canary needed +8M just to close its speed shortfall). FAIL - MECHANISM only if the anchor loss diverges/NaNs, or the held-out gait collapses (sacrificed leg, falls) at this budget.

**verdict**: Canary auto-stop at 5.67M/8M (protected walk_fwd 2/2->0/2, 3 consecutive checks) with reward still rising (quarters 216->1251) and the anneal never firing -- the hypothesis (more assay rounds will eventually hit a clean batch and latch the gate) is REFUTED by mechanism, not by budget. EVIDENCE: (1) bc_anchor_anneal/gate_pass=0 in all 11 rounds, coef pinned at 3.0 to the end; gate_early_term_rate exactly 0.125 in 10/11 rounds. (2) The assay is PINNED: env.seed(828282) before EVERY round, desync_episodes=False, deterministic policy -> the same 8 configs every round; the persistent 1/8 early-term is ONE config the anchored policy deterministically fails, not sampling noise (parent at 2M failed 2/8, later ckpts 1/8 -> policy-dependent falls, not a reset-time env rejection). There were never any 'more chances'. (3) Double lock: the early-terminated episode injects failed_probe_row() (cmd_prog_frac=NaN, plain-mean aggregation, not in _NAN_OK) so the progress clause ALSO NaN-fails every round (gate_cmd_prog_frac absent from W&B history in both seeds). (4) Held-out mesh gate eval: NO collapse -- gait_valid 24/24, 0 falls/terms, no sacrificed leg, video shows all six legs cycling behind the command arrow; but det prog med 0.30 (vs parent-2M 0.36-0.52, bar 0.35) while sto is 0.39-0.40 with better slip (2.98 vs det 4.48): the never-fading strong anchor increasingly compromises the deterministic mean as log-std anneals, matching the canary regression. Twin s1-cont8m shows the identical pattern (15 rounds all-fail at 0.125, coef 3.0, walk_fwd 0/2 from 5M). WHY: chicken-and-egg deadlock -- the latch demands zero falls on a frozen probe set containing a hard init, while the stuck-strong anchor prevents exactly the adaptation that would fix it; continued anchored training then actively degrades pinned det behavior. Per the 08-21 ruling this is misalignment to repair, not a lineage kill: the parent 2M checkpoints still pass the held-out ignition bar. NEXT: built+tested train.bc_anchor_anneal_assay_reseed (default OFF, bit-exact when off; fresh pinned seed per assay round -> independent draws; 9 tests green, snapshot exp/cw-assistfade-rung2-anchorfade-reseed-fix) and relaunched both seeds from the PARENT 2M checkpoints with reseed=1 (-reseed8m pair).

