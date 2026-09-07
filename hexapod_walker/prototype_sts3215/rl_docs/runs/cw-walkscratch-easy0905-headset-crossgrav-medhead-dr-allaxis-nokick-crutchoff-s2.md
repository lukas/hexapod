# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-07T04:43:23+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-c1-s2

**hypothesis**: Plain English: does turning the 3x torque-assist crutch OFF stop this composite's push-recovery falls, or does it fall anyway because push itself is the culprit? item(1)'s crutch-ON/kick-fully-off full-realism composite showed tilt_roll falls in 2/3 seeds even at a clean 2M canary (this exact seed, -s1, CANARY FAIL - MECHANISM) and the 3rd seed (s0) only failed once trained to 40M ACQ (2/24 falls). Both fall videos on s0's ACQ read show a push marker landing 1-2 frames before the robot topples, and the ONLY known-clean full-realism composite (allaxiskickhalf-nocrutch1x-c1-acq1-cont40m, 0 falls at both 40M and 80M) differs from the failing one on TWO axes at once (torque_scale 1x vs 3x, AND kick 0.15 vs 0.0), so crutch-vs-kick has never been isolated. This is the single-lever ablation: same seed/init-from/DR composite as the already-FAILED -s1 canary, kick stays fully OFF (matching the failing recipe, not reintroducing the half-dose from the clean composite), ONLY dr.torque_scale flips 3,3 to 1,1 (true unassisted servo gains). If CLEAN (0 falls, majority gait_valid) at the SAME seed that already fell with crutch ON: crutch is a real driver of the push-recovery fragility (surprising direction -- MORE assistive torque destabilizing recovery, plausible if the crutch's higher effective gain overshoots during a fast recovery response) -- worth extending to the s0/acq1 lineage next. If it FAILS THE SAME WAY (tilt_roll fall under push): crutch is not the driver, closes that half of the 30-axis composite's fragility and re-points the isolation search at push magnitude/timing itself or another untested axis interaction.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Ignition/composite-health canary read at 2M (same bar as the parent canary that already failed this exact seed): PASS if 0 falls/terminations across all 24 episodes AND gait_valid stays majority (at least 18/24) -- closes crutch as the driver, matched to this seed. FAIL if a tilt_roll (or any) fall reproduces on the SAME seed that already fell with crutch ON -- rules out crutch, re-points isolation at push or an untested axis. Read side-by-side with its s2 twin (seed 4) before drawing the 2-seed conclusion.

**verdict**: CANARY PASS (mechanism-health scope): matches its s1 twin. Removing the 3x torque crutch (dr.torque_scale 3,3->1,1) fixes this seed's push-recovery fragility too -- same seed/init-from as the already-FAILED c1-s2 2M canary, 0 falls/terminations across all 24 held-out episodes, gait_valid 20/24 (walk/det 6/6, walk/sto 5/6, startjitter/det 6/6, startjitter/sto 3/6) -- essentially identical numbers to s1's own read. 2/2 crutch-off single-lever ablations now clean on seeds that both fell with crutch ON: crutch is confirmed (not seed noise) as a real driver of item(1)'s push-recovery fragility. Next: matched 40M ACQ continuation launched this cycle (crutchoff-s2-acq1) to test scale durability, mirroring s1's own follow-up.

