# cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s10-acq1-cont10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RETENTION FAIL - DEGRADES FURTHER

**created**: 2026-09-08T11:48:11+00:00

**pod**: hexapod-mjx-train-1

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s10-acq1

**wandb_id**: 83az85kk

**hypothesis**: Matched joint-space (OFF) control for the seed10 cont10m durability read above: does this arm's own 40M performance (0 falls/24, speed 0.17-0.21 m/s, gait_valid 7/24) hold steady at 10M more steps, so the paired ON/OFF slip and gait_valid comparison at 50M is a valid depth read, mirroring seed7's own OFF cont10m (gait_valid degraded further 10/24->7/24).

**gate**: MATCHED CONTROL: read together with s10-acq1-cont10m at the same budget. Retention = 0 new falls and slip/m within noise (+/-20%) of this arm's own 40M read; report whether gait_valid holds at 7/24 or degrades further, same as seed7's OFF arm did.

**verdict**: The matched joint-space (OFF) seed10 arm answers its own pre-registered question directly: gait_valid degrades FURTHER with more training, from 7/24 at 40M to 4/24 at 50M (walk/sto 4/6->3/6, startjitter/sto 3/6->1/6, det and startjitter/det stay at the already-chronic 0/6 leg1-park). 0 new falls/terminations (24/24 clean) and slip/m held or improved in every group (1.97/1.92/1.90/1.99 vs 40M's 1.98/2.06/2.07/2.07). This is the gate's own named alternative outcome ("degrades further" vs "holds at 7/24") and it is the one that happened. Read jointly with the ON sibling's own retention read (also this cycle): both arms lose gait_valid with the extra 10M steps (ON 17->14, OFF 7->4) but the ON/OFF GAP is unchanged at exactly 10 points both times -- more training erodes six-leg health on both action spaces roughly proportionally rather than closing or widening the cart_foot advantage. No further continuation funded on this seed/recipe; the erosion direction (not just the seed7-vs-seed10-vs-seed11 gap-size spread) is now itself a repeated finding across 2 seeds (s10, s11) and belongs in CURRENT_TRUTHS. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_cartfoot_halfgrav_offctrl_s10_acq1_cont10m_gate/report.json vs the 40M report; W&B 83az85kk.

