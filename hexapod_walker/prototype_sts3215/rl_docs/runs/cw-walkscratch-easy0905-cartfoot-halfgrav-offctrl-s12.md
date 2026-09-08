# cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s12

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS

**created**: 2026-09-08T11:28:40+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s7

**wandb_id**: z8u4ay72

**hypothesis**: Plain English: matched joint-space control for the halfgrav cart_foot seed12 canary (ON launched same cycle) -- 4th-seed replicate breaking the tie in the closed n=3 cohort (2/3 seeds showed a cart_foot gait_valid advantage, 1/3 near-parity). Byte-identical to cartfoot-halfgrav-offctrl-s7 with only seed changed to 12.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY: finite losses, weights changing, real joint/foot excursion, no hidden limiter, reward/tick agreeing with the bank. NO WALKING AT 2M IS NOT A FAILURE. On PASS, extend to 40M acquisition and read together with the ON s12 sibling: same joint reading protocol as s7/s10/s11 (>=0.03 m/s median net forward in >=1 of walk/det,sto, 0 falls in det; slip/m and gait_valid vs ON sibling are the headline comparisons).

**verdict**: CANARY PASS (mechanism health, 2M): matched joint-space (OFF) canary for the seed12 tie-break pair. Finite losses/value/KL throughout (loss 820->700->526, approx_kl ~0.003-0.004, value_loss declining 1733->1220), zero training-time falls by the final window (tilt_roll 5->3->0->0 across quarters) and zero eval-time terminations in all 24 gate episodes. Real excursion under stochastic sampling (walk/sto, walk_startjitter/sto prog 0.11-0.49, fwd 0.09-0.58m, slip 11-133) vs near-static deterministic episodes (prog ~0.00, fwd ~0.00m) -- exactly the 'no walking at 2M is not a failure' shape every s7/s10/s11 offctrl canary showed at this same budget, same telemetry band. gait_valid reads 6/6 in all 4 groups but is not the headline at this depth (per gate text) since foot-contact patterns are dominated by near-stationary det episodes. Reward declining smoothly (quarters -138/-308/-471/-644) tracks ep_len_mean rising 108->233->360->485/500 under the walk_pure reward's per-tick shape, not instability. Matches the ON s12 sibling's own already-PASSED canary telemetry band (concurrent cycle). Per this gate's own text: extend to 40M acquisition and read together with the ON s12 sibling (already running its own 40M extension, cartfoot-halfgrav-s12-acq1, train-7) -- launching the matched OFF extension this cycle to complete the pair the ON hypothesis already presumes exists.

