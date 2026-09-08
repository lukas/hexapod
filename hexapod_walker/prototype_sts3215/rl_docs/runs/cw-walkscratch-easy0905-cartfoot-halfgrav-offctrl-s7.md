# cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s7

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS

**created**: 2026-09-08T08:33:31+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**wandb_id**: 2ck5m8dj

**hypothesis**: Matched joint-space control for cartfoot-halfgrav-s7 above: byte-identical recipe (fresh random init, halfgrav 0.5g, seed 7) minus the 3 cart_foot box keys (joint-space action decode instead). Establishes whether joint-space itself ignites cleanly at 0.5g+seed7 before any ON-vs-OFF ratio claim, mirroring the 1g fork(b) methodology exactly.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. 2M MECHANISM-HEALTH CANARY ONLY, same bar as its ON sibling. Read together with cartfoot-halfgrav-s7.

**verdict**: CANARY PASS: joint-space (OFF) control ignites cleanly at 0.5g+seed7 -- mechanism healthy, matches the already-proven base/1g-cartfoot ignition pattern. Finite/decreasing losses (train/loss 805->519, value_loss 1733->1213), std anneals 0.37->0.22 on schedule, KL small and stable -- no blowup. ep_rew_mean falls (-140->-646) but this is the SAME ep_len-growth artifact already established on the matched 1g fork(b) cartfoot-freshinit-offctrl-s7 control: ep_len_mean grows 101->223->353->488 while per-tick env/reward_walk actually RISES 0.178->0.170->0.196->0.218 and env/v_along_cmd_m_s ends positive (0.011, up from 0.005). Det mode is a settled near-static stance (fwd 0.00m, duty~0.99, 1-3 swings/20s -- expected per this canary's own gate text, not a failure), sto mode shows real forward displacement (fwd 0.21-0.57m, prog up to 0.48, slip 11-137/m) confirming genuine leg excursion beyond a frozen policy. 0 falls/terminations across all 24 episodes in every mode. Joint-space ignites just as cleanly at 0.5g as it already did at 1g and at full gravity -- no gravity-specific joint-space pathology. Read together with cartfoot-halfgrav-s7 (ON, also verdicted this cycle): both PASS, near-parity slip at this early stage (det 0.83 OFF vs 1.03 ON, sto 28.16 OFF vs 21.79 ON) -- unlike the 1g comparison where cart_foot eventually showed a 3-10x slip gap after long continuation, that comparison needs continuation depth to reveal here too, not visible from a 2M canary alone.

