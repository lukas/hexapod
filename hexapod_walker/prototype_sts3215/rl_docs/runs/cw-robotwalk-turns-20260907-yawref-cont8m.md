# cw-robotwalk-turns-20260907-yawref-cont8m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL - QUALIFICATION (partial)

**created**: 2026-09-07T10:10:32+00:00

**pod**: hexapod-mjx-train-1

**steps**: 8000000

**parent**: cw-robotwalk-turns-20260907-yawref-acq8m

**wandb_id**: pzu0hc62

**hypothesis**: Plain English: the frame fix (walk_course_ref_yaw + arc-aware sway + doubled yaw-progress pay) just DECISIVELY confirmed itself on its target metric (joygate course_yawref_err_1s_med 4.33deg, clears the 5.17deg bar, reward still climbing every quarter with no plateau) -- does another 8M of the SAME now-correctly-aligned recipe also close the one remaining named gap, tip-turn-in-place wz_err_med (0.0935/0.0809, over the 0.076 bar but flat vs the parent's 0.078/0.085, i.e. this exact combined-frame fix was never given a second budget increment to consolidate)? Straight continuation, init-from-source off this checkpoint, zero cfg changes -- the honest next question per the 08-21 ruling (reward rising + one gap open = continue, not stop) is whether tip improves as the now-aligned reward consolidates, or stays flat again (which would mean tip needs its own dedicated lever, not more of this budget). Prediction-if-true: tip wz_err_med drops below 0.076 both signs while course_yawref/walk-retention/standing-still all hold at least as well as the 8M read. Prediction-if-false: tip stays in the 0.08-0.095 band a second time under a real budget increase -- next step is a dedicated tip-in-place income lever (not a 3rd same-recipe continuation).

**gate**: PASS (ships, exports) if ALL: (a) tip both signs wz_err_med <0.076; (b) combined-cell wz_err (eval_yaw arc/arc-max) at or better than this run's own 0.0901/0.0905/0.2216/0.2251; (c) walk retained: DR-0 gate_valid 24/24 all 4 modes, 0 falls, walk/det fwd_m >=0.29/12s, slip<=2.9; (d) joygate stress_mix pass=true AND course_yawref_err_1s_med<=5.17deg; (e) cmd_suite stop cell stays near-zero v_err (no standing-still regression). CONTINUE (more budget, no export) if tip improves but does not clear 0.076, with (b)-(e) holding and reward still rising. FAIL-flag (stop this lineage, needs a dedicated tip lever) only if tip is flat-or-worse AND (b)/(d) also regress with reward flat -- per 08-21, reward still rising with only tip flat is informative-negative on tip specifically, not a lineage kill.

**verdict**: Honest partial/FAILED qualification: the 8M same-recipe continuation did NOT qualify for export -- its own pre-registered PASS branch fails on (a) and (b). Per-cell evidence (all original thresholds preserved, corrected course_yawref key retained): (a) tip-in-place wz_err_med 0.0885 left / 0.0842 right vs <0.076 bar -- STILL MISSED, net flat vs acq8m (0.0935/0.0809): 2nd consecutive budget increment with tip stuck in the 0.08-0.095 band, exactly the run's own pre-registered prediction-if-false. (b) combined cells vs acq8m 0.0901/0.0905/0.2216/0.2251: arc-left 0.0947 (+5%), arc-right 0.1162 (+28% REGRESSION, largest delta, same seed/cfg/det env so real), arc-left-max 0.2153 (better), arc-right-max 0.2243 (better) -- MIXED, (b) does not hold. (c) walk retention HOLDS: full DR-0 gate 24/24 gait_valid, 0 terms, walk/det fwd med 0.2905m >=0.29, slip/m 2.6885 <=2.9. (d) joygate stress_mix HOLDS+IMPROVES: pass=true, 0/24 falls, slip 2.295, course_yawref_err_1s_med 4.33->4.07deg (<5.17 Candidate-B bar, same corrected key both reads). (e) stop cell HOLDS: v_err_med det 0.0013 / sto 0.0037, wz_err ~0. Reward still rising (quarters 313/1350/2362/2964) so per 08-21 this is informative-negative on tip/arc-right specifically, NOT a lineage kill: walk+course+stop assets are intact and improving. Ruled next step (pre-registered in this run's own hypothesis): a DEDICATED tip/combined-turn mechanism lever, NOT a third identical 8M continuation. Turn-script video (tip-left/right 0.3, arc-left/right 0.15) capture registered as ..._turnvideo. Evidence: logs/ckpt_eval/cw_robotwalk_turns_20260907_yawref_cont8m_{gate,yaw,joygate_freshcmp}/ vs acq8m same dirs on train-1; W&B pzu0hc62.

