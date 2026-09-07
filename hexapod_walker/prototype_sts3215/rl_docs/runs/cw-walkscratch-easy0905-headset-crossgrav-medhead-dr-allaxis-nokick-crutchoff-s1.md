# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-07T04:41:00+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-c1-s1

**wandb_id**: w4ytxxft

**hypothesis**: Plain English: does turning the 3x torque-assist crutch OFF stop this composite's push-recovery falls, or does it fall anyway because push itself is the culprit? item(1)'s crutch-ON/kick-fully-off full-realism composite showed tilt_roll falls in 2/3 seeds even at a clean 2M canary (this exact seed, -s1, CANARY FAIL - MECHANISM) and the 3rd seed (s0) only failed once trained to 40M ACQ (2/24 falls). Both fall videos on s0's ACQ read show a push marker landing 1-2 frames before the robot topples, and the ONLY known-clean full-realism composite (allaxiskickhalf-nocrutch1x-c1-acq1-cont40m, 0 falls at both 40M and 80M) differs from the failing one on TWO axes at once (torque_scale 1x vs 3x, AND kick 0.15 vs 0.0), so crutch-vs-kick has never been isolated. This is the single-lever ablation: same seed/init-from/DR composite as the already-FAILED -s1 canary, kick stays fully OFF (matching the failing recipe, not reintroducing the half-dose from the clean composite), ONLY dr.torque_scale flips 3,3 to 1,1 (true unassisted servo gains). If CLEAN (0 falls, majority gait_valid) at the SAME seed that already fell with crutch ON: crutch is a real driver of the push-recovery fragility (surprising direction -- MORE assistive torque destabilizing recovery, plausible if the crutch's higher effective gain overshoots during a fast recovery response) -- worth extending to the s0/acq1 lineage next. If it FAILS THE SAME WAY (tilt_roll fall under push): crutch is not the driver, closes that half of the 30-axis composite's fragility and re-points the isolation search at push magnitude/timing itself or another untested axis interaction.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Ignition/composite-health canary read at 2M (same bar as the parent canary that already failed this exact seed): PASS if 0 falls/terminations across all 24 episodes AND gait_valid stays majority (at least 18/24) -- closes crutch as the driver, matched to this seed. FAIL if a tilt_roll (or any) fall reproduces on the SAME seed that already fell with crutch ON -- rules out crutch, re-points isolation at push or an untested axis. Read side-by-side with its s2 twin (seed 4) before drawing the 2-seed conclusion.

**verdict**: CANARY PASS (mechanism-health scope): removing the 3x torque crutch (dr.torque_scale 3,3->1,1) fixes this seed's push-recovery fragility. Same seed/init-from as the already-FAILED c1-s1 2M canary (which fell with crutch ON); this crutch-off single-lever ablation clears the pre-registered bar: 0 falls/terminations across all 24 held-out episodes, gait_valid 20/24 (walk/det 6/6, walk/sto 5/6, startjitter/det 6/6, startjitter/sto 3/6), no regression vs the crutch-ON canary's own gait_valid/walking quality. Frame strips (walk_det_0, walk_startjitter_sto_3) show a level, upright body walking under a push perturbation with no topple. Confirms the 3x torque assist itself was a driver of the fragility (surprising direction: MORE assistive torque destabilizing fast recovery, plausibly via gain overshoot), not push magnitude/timing or an untested DR axis. Next: matches its s2 twin (also CANARY PASS this cycle) -- 2/2 crutch-off arms clean, licensing a matched 40M ACQ continuation to test whether this holds at scale (s0's own crutch-ON failure only appeared at 40M, not 2M) -- launched this cycle as crutchoff-s1-acq1.

