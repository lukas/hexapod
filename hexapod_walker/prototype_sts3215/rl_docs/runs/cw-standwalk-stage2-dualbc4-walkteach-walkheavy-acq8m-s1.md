# cw-standwalk-stage2-dualbc4-walkteach-walkheavy-acq8m-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-08-31T00:59:40+00:00

**pod**: hexapod-mjx-train-2

**steps**: 8000000

**parent**: cw-standwalk-stage2-dualbc4-walkteach-walkheavy-acq8m

**wandb_id**: bheflsxm

**hypothesis**: Seed-1 twin of cw-standwalk-stage2-dualbc4-walkteach-walkheavy-acq8m (see its ledger hypothesis): paired seed replicating the walk-heavy goal-mix fix for the pooled-mix walk regression the acq8m pair showed.

**gate**: ACQUISITION (own-scope), joint with seed0: pure-walk det read (_gate harness walk/det + startjitter, mode_seq OFF) progress_ratio med >=0.44 AND slip/m med <=2.9 AND gait_valid >=5/6, sacrificed legs 0, zero walk terminations, course_err_1s_med not worse than 3.4deg band; RETENTION: rise_det and lower_det not collapsed vs the acq8m-s1 gate read.

**verdict**: FAIL -- the walk-heavy diet fix (mix 0.60 walk vs the parent acq8m-s1's 0.30) did NOT recover the pure-walk progress regression it was launched to fix. Own pure-walk det read (mode_seq=0 forced override, gate cfg, n=8, retrieved from train-2 where it finished hours ago but was never copied back or verdicted -- closing that gap this cycle): progress_ratio med 0.3765 (range 0.337-0.399), ALL 8 episodes below the gate's own >=0.44 bar and essentially unchanged from the just-failed acq8m-s1 parent's own 0.373/0.379 read -- the mix-share lever moved nothing. slip_per_m med 2.85 (2.72-3.98) clears the <=2.9 bar, gait_valid 8/8, sacrificed_legs 0/8, zero terminations -- clean gait, just slow/underpowered (frame strip: full tripod-alternating six-leg cycling, real forward translation, no flag leg, no drag -- confirms a speed-soft read, not a collapse). RETENTION clause (own gate/owncfg mixed-session, mode_seq=0.75): rise/det 6/6 success, lower/det 6/6 success, zero terminations both -- retention held, so the walk-heavy remix did not trade away the acq8m rise/lower gains it was designed to keep. Root cause not walk-heavy-mix-shaped: the regression this arm targeted was never actually about diet share; it likely traces to the same BC-anchor-dilution-adjacent or optimization-dynamics territory the concurrent turn-authority campaign later found on this same dualbc4/dualbc5 lineage family. Do not fund a further mix-share dose on this lever -- diet share is now exonerated for BOTH the progress regression (this arm) and turn authority (dualbc4/5 turn campaign), leaving optimization dynamics as the shared suspect for future work on this lineage. Evidence: logs/ckpt_eval/cw_standwalk_stage2_dualbc4_walkteach_walkheavy_acq8m_s1_{purewalk_det,gate,owncfg}/report.json (pulled from train-2 this cycle), frame strip cw_standwalk_stage2_dualbc4_walkteach_walkheavy_acq8m_s1_gate/walk_det_0.png.

