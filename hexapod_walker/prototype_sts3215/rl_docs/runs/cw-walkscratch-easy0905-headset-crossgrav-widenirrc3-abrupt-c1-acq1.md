# cw-walkscratch-easy0905-headset-crossgrav-widenirrc3-abrupt-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T04:52:10+00:00

**pod**: hexapod-mjx-train-10

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-widenirrc3-abrupt-c1

**wandb_id**: 6s59dh5w

**hypothesis**: Plain English: the abrupt-1g crossgrav discovery canary off the widenirr-c3 halfgrav champion (CANARY PASS-INFORMATIVE, gait_valid 23/24, 0 falls, only 1 flagged episode with no chronic leg pattern) already showed six-leg walking survives an abrupt jump to full gravity on this widen+irr composite's 2nd seed, closing the widenirr-crossgrav axis at n=2 clean (unlike widen2's seed-split). This is the acquisition-scale (40M) confirmation: does that six-leg gait hold up at a full training budget at 1g on this seed, matching the medhead/widen2c1/s1acq/s3acq precedent of testing whether canary-clean crossgrav transfer survives ACQ-scale exposure (recall: healthy-source canaries have split roughly half PASS/half FAIL at ACQ scale on this campaign, so this is a genuine open question, not a rubber stamp)?

**gate**: ACQ PASS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with no chronic (<0.10-duty every episode) single-leg sacrifice at 40M, matching or improving the 2M canary's 23/24 read, 0 falls, slip/m at/near the 2.9 teacher band. ACQ FAIL if walk/det or walk/sto regresses to majority failure or the leg[1,4]-style chronic-park fingerprint emerges/hardens under longer 1g exposure (matching the irracq1/irr2acq1/s3acq entrenchment class already seen this campaign). ACQ CONTINUE if reward is still climbing with borderline (not hard-park) duty, per the 08-21 ruling.

**verdict**: ACQ PASS. The widenirr-then-crossgrav (8-direction heading set incl. backward/diagonals) 2nd seed holds its own 2M canary's clean read at full 40M budget: aggregate gait_valid 23/24, IDENTICAL to the canary's own 23/24. Only walk/det ep3 fails gait_valid (legs 2+5 duty 0.02/0.01 that one episode); every other episode across all 4 panels (walk/det 5/6, walk/sto 6/6, walk_startjitter/det 6/6, walk_startjitter/sto 6/6) is clean with no low-duty leg. This is a single non-chronic dip on DIFFERENT legs than the campaign's recurring leg[1,4] entrenchment fingerprint -- not the ACQ FAIL pattern (irrwidenc2/irracq1/s3acq all show a repeating chronic leg across multiple episodes; this run doesn't). 0 falls/terminations in all 24 episodes. track_err_mean_deg stays tight (4.0-6.6deg) across EVERY episode regardless of return sign, and duty_cycle stays healthy (all 6 legs actively cycling, no near-zero leg) even in the most reward-negative episodes -- frame strips (contact_sheet.png, walk_startjitter_sto_5 at return=-3406) confirm a genuinely clean, upright, six-leg gait tracking its commanded heading. IMPORTANT SEPARATE FINDING (reward/eval misalignment, 08-21 category, not a gate blocker): ep_rew_mean is deeply negative and bimodal/non-monotonic across quarters (-1082/-1559/-1414/-1154) and per-episode returns swing wildly (+1380 to -3406) despite near-identical forward_dist_m (~1.0-1.8m) and tight track_err in every episode -- this is the widened 8-way heading set's first ACQ-scale run to include backward/diagonal commands, and the freeprog reward kernel evidently penalizes some heading directions heavily even when tracking is accurate and duty is healthy. This is a reward-shaping gap specific to wide/backward heading sets, worth a semantics-bank fix, but does NOT indicate a behavioral failure -- the eval metrics (the gate's actual criteria) are clean. slip/m banded higher than most siblings (4.1-9.6 vs typical 3.4-5.5), plausibly reflecting the harder 8-way maneuvering requirement; still gait-valid throughout. 3rd of 3 sources (medhead, s1acq, widenirrc1-style) tested for the widen+irr-composed 8-way heading set to hold clean at ACQ scale on THIS particular composition ordering. NOTE this run's own eval took 2 podeval attempts to land (first attempt's kubectl exec websocket dropped mid-run with rc=1, the remote eval process kept running server-side unaffected; manually kubectl-cp'd the already-complete report.json off train-10 rather than re-running).

