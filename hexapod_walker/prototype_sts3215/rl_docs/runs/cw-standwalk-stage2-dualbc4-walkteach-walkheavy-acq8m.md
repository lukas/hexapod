# cw-standwalk-stage2-dualbc4-walkteach-walkheavy-acq8m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-08-31T00:53:50+00:00

**pod**: hexapod-mjx-train-1

**steps**: 8000000

**parent**: cw-standwalk-stage2-dualbc4-walkteach-anchor14coef1-acq8m-s1

**wandb_id**: 5qbrore2

**hypothesis**: Plain English: if walking gets the MAJORITY of the training budget instead of 30%, the 8M unified-policy continuation should hold or improve walk progress instead of quietly trading it away for rise/lower/hold reward - which is exactly what the failed acq8m pair did (acq8m-s1 verdict: pooled reward rose -100->705 entirely from the 70% non-walk mix while pure-walk det progress regressed 0.463->0.373 and slip 1.77->2.83; walk-specific reward channels flat/declining the whole run). Single delta vs the failed arm: goal-mix walk=0.60,rise=0.20,lower=0.10,hold=0.10 (same init ppo_goal_cw_standwalk_stage2_dualbc4_walkteach_anchor14coef1_canary_s1.zip, same cfg/reward stack, same 8M). Prediction-if-true: pure-walk det prog >=0.44 and slip <=2.9 at 8M with rise/lower det retention intact (the BC anchor held stance skills at low exposure throughout the dualbc lineage). Prediction-if-false: walk still regresses -> mix share is exonerated and the suspect becomes the pooled-gradient/anchor interaction itself (next lever: walk-quality regression canary or separate walk value head). Strongest alternative: rise/lower/hold erode at reduced share - caught by the retention clauses.

**gate**: ACQUISITION (own-scope): pure-walk det read (the _gate harness walk/det + startjitter, mode_seq OFF - NEVER own-cfg mode_seq fastchecks, see 08-31 STATUS tooling trap) progress_ratio med >=0.44 AND slip/m med <=2.9 AND gait_valid >=5/6, sacrificed legs 0, zero walk terminations, course_err_1s_med not worse than the failed acq8m's 3.4deg band; RETENTION: rise_det and lower_det success/medians not collapsed vs the acq8m-s1 gate read (rise/lower were the modes the failed arm improved - holding most of that while fixing walk is the win condition). Joint with -s1 twin.

**verdict**: FAIL, joint with the already-FAILed -s1 twin -- the walk-heavy diet fix (mix 0.60 walk vs the parent's 0.30) did NOT recover the pure-walk progress regression on seed0 either. Own pure-walk det read (mode_seq=0 forced override, gate cfg, n=8, launched last cycle on train-3, pulled back this cycle): progress_ratio med 0.3775 (range 0.362-0.407), every episode below the gate's >=0.44 bar and matching the -s1 twin's 0.3765 almost exactly -- the mix-share lever moved nothing on this seed either. slip_per_m med 4.15 (2.71-4.64), ALSO over the <=2.9 bar (worse than -s1's 2.85, which barely cleared it) -- a second, independent gate clause fails here. gait_valid 8/8, sacrificed_legs 0/8, zero terminations -- own contact-sheet reviewed, clean tripod-alternating six-leg gait, no flag leg, no drag; a speed-soft/slow read, not a collapse. Root cause: same as -s1's verdict -- diet share is exonerated as the lever (both seeds regressed identically despite the mix change), leaving optimization dynamics on this dualbc4/dualbc5 lineage family as the shared suspect (the same territory the concurrent turn-authority campaign later converged on). Joint gate CLOSED both seeds FAIL; no further mix-share dose funded on this lever. Hardware-ready: no.

