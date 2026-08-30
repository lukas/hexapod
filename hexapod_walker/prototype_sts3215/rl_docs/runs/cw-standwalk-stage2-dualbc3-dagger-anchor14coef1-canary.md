# cw-standwalk-stage2-dualbc3-dagger-anchor14coef1-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-08-30T11:21:22+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc2-allheadwalk-anchor14coef1-canary

**wandb_id**: ukswqzha

**hypothesis**: Plain English: the dualbc2_allheadwalk Stage-2 BC base checkpoint never walked forward pre-RL (root-caused to BC compounding error), so its anchor14coef1 canary FAILED on an already-broken base -- does the SAME anchor14coef1 recipe now succeed when re-init'd from dualbc3_dagger, the DAgger-repaired replacement (byte-identical distillation recipe + 2 rounds/100-episode DAgger)? Pre-flight quick_probe re-run this cycle (fixed-heading, n=2, weights-only reload of the saved zip, no retraining) confirms the fix actually cleared the bar the STATUS.md Next item required: walk-mode net_disp_m 0.463/0.493 over a 15s fixed-heading episode (was 0.004-0.026m for dualbc2, an order of magnitude below the 0.05m in-place-quiver threshold) -- this is a genuinely walking base checkpoint now, so funding the RL canary is warranted per the track's own gating rule.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY, same convention as the dualbc2 pair: WIRING CHECK train/bc_anchor_loss_walk + train/bc_anchor_fill_walk nonzero every logged update. PASS/promote-to-8M-acquisition if BOTH seeds show det walk gait_valid>=5/6, zero/near-zero sacrificed legs, progress_ratio clears the 0.10-0.18 band anchor14 showed on the old teacher. PARTIAL (fund 8M anyway) if gait_valid holds but progress stays flat. FAIL if anchor4-class catastrophe (gait_valid 0-1/6, sacrificed legs) OR probe pathologies worsen under RL -- but note the upstream base is now pre-verified walking net-forward, so a FAIL here would implicate the anchor14coef1 recipe/RL fine-tune itself rather than an already-broken base (unlike the dualbc2 pair).

**verdict**: CANARY PASS on the DAgger-repaired Stage-2 base -- promoted to an 8M acquisition continuation. Evidence: fast det+sto no-video reads on a spare pod (train-2, weights unchanged) since the ledger's own video-bearing gate/owncfg were still mid-flight (~1h ETA): det walk gait_valid 8/8, sacrificed_legs=[] every episode, 0/8 terminations, progress_ratio 0.28 (forward_dist_m 0.63-0.65m/30s at speed 0.037 m/s) -- clears the anchor14 0.10-0.18 old-teacher band with real margin, slip/m 3.39 (course_err_1s med 5.9deg -- short-window heading tracking is clean despite a high full-episode direction_err_mean 62deg, a low-speed-early-episode artifact, not a wrong-way walk). Sto mode weaker (prog_ratio 0.04, slip/m 17.1) but still net-forward (fwd 0.09-0.12m/30s), zero falls/sac -- expected 2M-canary softness, not the gate's own pass criterion (det walk). WIRING CHECK also clean (bc_anchor_loss_walk 0.002-0.006 falling, bc_anchor_fill_walk 12k->38.7k monotonic every logged update, direct from cached wandb_history.csv). Why this matters: this is the first anchor14coef1 canary run on a base checkpoint independently pre-verified to walk net-forward (quick_probe net_disp 0.463m/15s) -- the dualbc2 pair's FAILs traced entirely to a broken BASE, not the recipe; this result shows the SAME recipe genuinely acquires skill (not just avoiding catastrophe) once given a real walking base. Next: promoted -- launched cw-standwalk-stage2-dualbc3-dagger-anchor14coef1-acq8m (8M, train-0, same std-anneal bundle as the anchor14-walkretaincoef1-rescue-acq8m precedent: --log-std-final -4.0 --log-std-anneal-frac 0.5 --gru-dual-log-std-split --log-std-anneal-core stance).

