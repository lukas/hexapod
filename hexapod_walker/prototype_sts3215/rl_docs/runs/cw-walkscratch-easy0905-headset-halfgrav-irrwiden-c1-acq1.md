# cw-walkscratch-easy0905-headset-halfgrav-irrwiden-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ PASS

**created**: 2026-09-05T23:48:05+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-irrwiden-c1

**wandb_id**: gmz0a4i2

**hypothesis**: Plain English: irrwiden-c1's 2M canary showed that composing the widen2 heading-widen step (5-way medhead -> full 8-way compass incl reversals) ON TOP OF the mature irr-timing-jitter champion (jitter-first order) keeps the gait cleanly valid (23/24, 0 falls, only one transient leg flag) -- the cleanest read of the whole widen2 family, beating both widen2-c1's (21/24) and widen2-c2b's (16/24) own 2M canaries. This is the acquisition-scale (40M) confirmation: does this composite champion (heading breadth + timing irregularity together) hold up at full budget the way widen2-c1-acq1 did (ACQ PASS, 21/24, 0 falls, slip improved vs canary), or does it entrench a chronic leg sacrifice at 40M the way the matched-seed sibling widen2-c2b-acq1 did (ACQ FAIL, gait_valid dropped 16/24->14/24, leg-1 chronic park)? This produces the first acquisition-scale test of the ACTUAL composite DONE-gate shape (heading set + irregular direction-change timing together), not one axis at a time.

**gate**: ACQ PASS if gait_valid stays majority (>=18/24) with 0 falls AND direction_err/course_err at the reversal headings continues to look like this run's own 2M canary read (walk/det dir_err med ~68deg, slip med ~6.4/m) rather than degrading toward the cold fullhead-c1 baseline's failure range (28-161deg, 0/24 success) or entrenching a chronic single-leg sacrifice the way widen2-c2b-acq1 did. ACQ FAIL if gait_valid drops into minority (<18/24) or any leg is chronically sacrificed (flagged sacrificed in >=1/3 of episodes, matching the widen2-c2b-acq1/base-family entrenchment fingerprint). ACQ CONTINUE if reward is still climbing and gait stays valid but course-tracking is still improving/ambiguous at 40M.

**verdict**: ACQ PASS: the widen+irr composite champion (jitter-first order, the actual DONE-gate panel shape -- heading breadth AND irregular timing together) holds at the full 40M acquisition budget. Harness gait_valid 22/24 (walk/det 5/6, walk/sto 5/6, walk_startjitter/det 6/6, walk_startjitter/sto 6/6), 0 falls/terminations in all 24 episodes. Only 2/24 episodes flag any sacrificed leg (one triple [2,4,5], one single [2]) -- scattered, not chronic, well under the 1/3-episode FAIL trigger; the rest are clean. Per the gate's own explicit comparison: walk/det course_err_1s_med median ~61deg and slip_per_m median ~5.9 are AT OR BETTER than this run's own 2M canary read (~68deg/~6.4 per the ledger gate text), not degrading toward the cold-jump fullhead-c1 baseline's failure range (28-161deg, 0/24 success). Video (walk_det_0, walk_det_3) confirms genuine six-leg cycling with the command arrow visibly flipping per the irregular resample timing. FLAGGED FOR THE RECORD (not a fail signal): ep_rew_mean is deeply negative (~-1500 to -2000, plateaued) -- root-caused to the always-on ungated reward_walk_freeprog_pen cross-track/backward charge sitting near its -2.0 ceiling most of the run because reversal headings are intrinsically hard to track; this same negative/declining shape was ALREADY present at the 2M canary (-608 at 2M end), so 40M continues the same trajectory rather than introducing a new degradation, and eval quality does not degrade -- exactly the reward-misaligned-with-eval pattern the 08-21 ruling says to continue through, not stop on. Course-tracking is still loose in the worst episodes (one sto ep hits wrong_course_frac_1s 0.737, course_err_1s_med 126deg) -- acquisition-scale mechanism confirmation, not a mature tight-tracking pass. SKILLS.md updated.

