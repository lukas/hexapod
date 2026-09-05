# cw-walkscratch-easy0905-headset-base-s0c1-placementjit-fresh

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T22:48:46+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-base-s0c1

**wandb_id**: h53uw7zb

**hypothesis**: Plain English: FROM-SCRATCH bake-in twin of the placementjit hypothesis (see irr-placementjit-c1 for the full code citation/theory) -- mirrors the campaign's own established fresh-vs-retrofit split (dgfresh/swinggate-fresh both baked their mechanism in from this exact lightly-trained 2M s0c1 checkpoint rather than retrofitting a 40M-entrenched one). Both prior reward-price mechanisms failed IDENTICALLY whether baked-in-early or retrofitted-late, which argued the pathology is not a late-training reward-optimization artifact. If placement-jitter (a state-distribution fix, not a reward price) ALSO fails from-scratch the same way, that is evidence the leg-favoritism habit forms very early regardless of when any fix is applied; if it succeeds specifically from-scratch (unlike the retrofit arms), that would show the fix needs to shape exploration from the start rather than retrofit an entrenched policy -- either outcome is informative and arm 3/3 completes a clean fresh-vs-retrofit x new-mechanism read.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (2M): repair-signal if the eventual walk_startjitter/det panel (once this checkpoint gets the same 40M-class scrutiny as its siblings) shows majority-clearing duty on legs that would otherwise entrench per this family's precedent, with 0 new falls and plain walk/det staying majority-valid. At this 2M canary stage: PASS/INFORMATIVE if ep_rew_mean and env/v_along_cmd_m_s show healthy monotonic learning (matching the s0c1/dgfresh/swinggate-fresh siblings' own healthy 2M canary shape) with 0 falls -- FAIL only on behavioral impossibility (flat reward, no forward velocity) which would indicate the injected start-pose noise is too disruptive at this dose to learn from at all.

