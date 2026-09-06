# cw-robotwalk-turns-20260906-cont8m-resume1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T05:24:48+00:00

**pod**: hexapod-mjx-train-9

**steps**: 3871232

**parent**: cw-robotwalk-turns-20260906-cont8m

**hypothesis**: Recovery of the SAME seed0 bounded +8M turns continuation after root mistakenly treated the initial8M allocation as a permanent cap. Main walking task clarified standing authorization. Retain killed source record7wzm9ybl; resume validatedmd5 f591835ca44bf799c894cdf323d9006f at4,128,768 of8,000,000 continuationsteps for remaining3,871,232 requestedsteps (PPOrollout rounding may add atmost one rollout). Same fullgravity mesh100Hz recipe, policy+optimizer retained; omit initial warm-log-std reopening and anneal from retainedvalue to-4 over remaininginterval. Original8M24/24 gait, zero falls, matchedslip gain and risingreward337->1136->1917->2418 justify completion; this is not anotherseed or new8M budget. If yaw/courseplateau, auditreward alignment rather than identical extensions.

**gate**: Original absolute gates, no relaxation: both tip signs correct yaw sign and wz_err_med<0.076; combinedvx0.08,wz=+-0.2..0.3 correctsign and improvedcourse vs CandidateB on identicalcells; eightheading deterministic12s zero falls, positiveprogress all, forward>=0.29m, slip/m<=2.9, no sacrificedlegs; stress_mix joystickpass AND per_pass.dr0.course_err_1s_med<=5.17deg explicitly asserted; clean translation, reverse, release, botharcsvideo. Existingcmdsuite+-0.15arc cells are insufficient and joygatepassalone doesnotassertcourse. Evaluate fullgravity matched sourceconfigs and freshCandidateB.

**refused_reason**: hexapod-mjx-train-9 already runs cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-cmddrop1x-c1 — GPU pods host exactly one run; pick a free GPU pod.

