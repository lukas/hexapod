# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-cartfoot-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS

**created**: 2026-09-08T05:32:34+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m

**wandb_id**: gzyvhnzt

**hypothesis**: Plain English: the scratch walk champion's ~5-6/m slip floor survived nine slip-pricing reward arms, DR-band narrowing, a torsional-friction dose and the action-clip controllability probe -- the one named remaining structural lever is HOW foot placement is parameterized, so this arm reinterprets the SAME 18 actions as per-leg Cartesian foot targets (leg-root-frame box 6/3.5/4 cm around the source decode's exact a=0 stance-foot point, exact model-derived analytic IK, FK parity 1.8e-16 m; reward/plant/SafetyLayer/motor contract and RNG2 untouched, keys default-off bit-exact) and asks whether the cont40m champion, warm-started with its joint-space skills scrambled under the new action semantics, RE-ACQUIRES walking through the foot-space parameterization in 2M and where its slip lands vs the matched off control. Mechanism evidence: 12/12 local bank (test_cart_foot_decode.py + root's test_cart_foot_frame.py) + root's GPU/Warp env bank PASS (artifacts/rl_watchdog/cart_foot_gpu_bank_20260908, decode parity 0.0 rad under DR/pool restore, hashes == snapshot b24c2ffa). Prior-free: pure kinematic action reparameterization, no clock/teacher/prior.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. 2M canary, standard 24-ep walk/walk_startjitter det+sto gate read AGAINST the byte-identical cartfoot-offctrl control: MECHANISM-VIABLE if 0 falls/terminations and gait_valid >= 18/24 with six-leg cycling on the contact sheet; PROMISING (fund an ACQ continuation) if additionally mean slip_per_m beats the off control in >=3/4 groups; FAIL-MECHANISM if it cannot re-acquire (falls, or gait_valid < 12/24 with reward flat). Per the 08-21 ruling, partial re-acquisition with reward still rising licenses a continuation, not a STOP. A 2M read is acquisition/mechanism evidence, not class closure.

**verdict**: CANARY PASS (mechanism-viable per its pre-registered bar; NOT promising at 2M): the Cartesian foot-placement action decode re-acquires genuine walking from a fully scrambled warm-start in 2M steps -- gate 19/24 gait_valid (det 5/6, sto 4/6, sj/det 4/6, sj/sto 6/6), ZERO falls/terminations in all 24 episodes, upright six-leg stepping on the contact sheet. But the PROMISING bar (slip beats the matched off control in >=3/4 groups) decisively FAILS: slip/m 19.1/25.0/68.4/32.8 vs offctrl 5.3/5.2/6.3/5.9 (3-10x worse in 4/4) with progress_ratio 0.31-0.51 vs 1.5-1.7 -- at equal +2M the foot-space parameterization walks far more slippily and slowly than the joint-space decode retains. train ep_rew_mean DECLINED monotonically (-61 -> -224) while eval walking improved to 0-fall; reward/eval divergence unresolved at this depth. Read honestly: 2M mostly measured RE-ACQUISITION through new action semantics (notable that it cleared 0 falls), not asymptotic slip; the inductive-bias-lowers-slip hypothesis is UNSUPPORTED at 2M retrofit depth, not closed. Mechanism itself is healthy (12/12 bank, GPU/Warp env bank PASS, decode parity 0.0 rad, fps cost ~10%). Next fork (not pre-licensed, deliberately left for the next cycle): a 10M ON continuation (mirrors the duty-charge 10M protocol) to separate re-acquisition transient from asymptote, vs closing the retrofit form and testing the parameterization fresh-init where it competes on equal footing. Evidence: logs/ckpt_eval/..._cartfoot_c1_gate/report.json (train-4), artifacts/rl_watchdog/walkcurr_cartfoot_20260908/, W&B gzyvhnzt, snapshot b24c2ffa.

