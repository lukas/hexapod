# cw-assistfade-rung3-residualfade-s1-nostdanneal

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-07T14:28:14+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**wandb_id**: u2kbwm2o

**hypothesis**: 2nd seed of the nostdanneal disambiguation pair (see s0-nostdanneal's hypothesis for the full root-cause writeup): removes the log_std-anneal/blend-anneal schedule collision that closed 6/6 prior rung3 arms by dropping --log-std-final/--log-std-anneal-frac entirely, single lever vs the original failed rung3-residualfade-s1 canary.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Identical ignition bar to s0-nostdanneal: progress_ratio>=0.35 all modes, zero falls/terminations, six-leg participation, det+sto held-out DR-0, eval with goal.walk_residual_gate=0. 2-seed pair needed before either PASS or FAIL is treated as closing the std-anneal axis (matches this track's own 2-seed replication discipline).

**verdict**: CANARY FAIL - MECHANISM: 2nd seed replicates s0-nostdanneal's outcome, closing the disambiguation pair 2/2. Ignition bar missed: walk/det gait_valid 0/6 (all 6 sac legs [0,5], all 6 TERM over_current, prog med only 0.09 -- no deceptive-high-progress artifact this seed, straight ignition miss); walk/sto gait_valid 1/6; startjitter/det 0/6, startjitter/sto 4/6. wandb_history.csv shows the same pre-registered FAIL shape as s0: reward peaks ep~200 (217) then declines to 119 final (quarters [101.0,167.5,134.6,125.5]), env/walk_loadslip_ratio climbs 0.2->5.0, terminations/over_current climb 0->42 mid-run. **2/2 seeds confirm: fully disabling the forced std anneal does not rescue rung 3 -- closes the std-anneal axis.** Per the doc's own pre-registered reading note, this exhausts every named rung-3 schedule lever (bare, stdslow, latehandover, longbudget, nostdanneal x2) and, combined with rung 4's own closure naming the phase-sv-contact reward diet itself (not its handoff schedule) as the blocker, leaves NO untried repair lever across rungs 2-4. Track-level finding: only rung 0 (persistent BC anchor, PROVEN) reaches the ignition gate; every anchor-removal/anchor-fade/residual-bound/phase-only variant tried on mesh/100Hz converges to the same high-slip leg-sacrifice or static-basin failure once the assist is genuinely withdrawn. Licenses a walkcurr-style DONE-NEGATIVE writeup for the assist-removal axis rather than a 7th schedule variant; see track STATUS.md update this cycle.

