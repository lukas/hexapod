# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-overspeedq1-cont8m-lswin

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-07T17:23:06+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-overspeedq1-cont8m

**wandb_id**: park94cw

**hypothesis**: Plain English: every direct slip charge tried so far escaped its own price by making the robot go FASTER, because extra speed was free income and grew the progress denominator of the slip/progress ratio - now that a separate charge prices overspeed, the same windowed slip charge should finally have to clean up the feet instead. Mechanical evidence (09-07 audit of the 4 closed arms): env/v_along_cmd_m_s rose 0.065->0.085-0.087 within EVERY closed 2M slip-arm window; loadslip-windowed-{s0,s1} halved their charge (-0.80->-0.38, windowed ratio 10.8->6.8) mostly via the prog-rate denominator while held-out slip/m never moved (4.83/5.05 vs 5.065 baseline); the overspeedq1-cont8m parent (this run's warm-start) is speed-controlled (v_along 0.074, det prog 1.336) but slips WORSE per meter (5.82) because foot motion never changed. Single delta vs the parent recipe: arm the bank-proven windowed loadslip dose (gate=1.0 ok=3.0 max=8.0 k=10.0 window_s=1.0 floor=0.01 m/s) ON TOP of the active overspeed charge (k_over=1.0, inherited). Combined-mechanism bank WALKCURR_OVLS (test_task_semantics.py, snapshot exp/walkcurr-ovls-interaction-bank ba9ae210) is 4/4 green incl. the escape-open control (loadslip-alone: 1.7x-cap gait matches at-cap) and escape-closed claim (combined: optimum decisively at the cap).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY + interaction read; do not judge mature gait. Baselines: warm-start parent overspeedq1-cont8m gate (walk/det slip/m med 5.82, prog med 1.336, gv 22/24, 0/24 falls), slip-only controls loadslip-windowed-{s0,s1} on the frozen cont40m (slip 4.83/5.05, no better than bare 5.065), frozen cont40m itself (4.98). INTERACTION SUPPORTED if held-out walk/det slip/m med drops >=1.0/m below the cont8m parent (<=4.8, beyond the ~0.5 episode-noise band) WITHOUT the speed escape reopening (train env/v_along_cmd_m_s must stay <=0.080; slip improvement must come with env/walk_loadslip_ratio falling while v_along is flat/down, i.e. numerator not denominator) and WITHOUT prog collapse (gate prog med >=0.75), gv >=18/24, 0 falls. FAIL-INTERACTION if slip stays within noise of the parent (>=5.3) or improves only via further slowing (prog med <0.75 or v_along dropping toward the idle floor) - closes the overspeed-x-ratio-charge interaction, next lever is contact/friction model fidelity or boundary-accept per the 09-06 closure. FAIL-EXPLOIT if gv <18/24 beyond the parent's own leg-2 cells, a new chronic leg appears, or any fall. No retroactive gate edits.

