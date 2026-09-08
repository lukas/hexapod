# cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s11-acq1-cont10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PARTIAL

**created**: 2026-09-08T11:51:15+00:00

**pod**: hexapod-mjx-train-3

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s11-acq1

**wandb_id**: pwphlkog

**hypothesis**: Matched joint-space (OFF) control for the seed11 cont10m durability read above: does this arm's own 40M performance (0 falls/24, speed 0.17-0.21 m/s, gait_valid 10/24, near-parity with ON's 11/24) hold, degrade or diverge from ON at 10M more steps -- seed11 is the outlier pair (near-parity, not a real ON/OFF gap at 40M), so this depth read tests whether the gap opens up late like seed7's did, or the near-parity holds.

**gate**: MATCHED CONTROL: read together with s11-acq1-cont10m at the same budget. Retention = 0 new falls and slip/m within noise (+/-20%) of this arm's own 40M read (1.82/1.89/1.83/1.94). Report whether the near-parity gait_valid (10/24 vs ON 11/24) holds, or a gap opens at depth like seed7 showed (22/24 vs 10/24).

**verdict**: OFF (joint-space) seed11 cont10m retention is PARTIAL, not a clean HOLD. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_cartfoot_halfgrav_offctrl_s11_acq1_cont10m_gate/report.json (24 episodes), wandb pwphlkog. Slip/safety retained: slip/m 1.76/1.93/1.77/1.74 (det/sto/startjitter-det/startjitter-sto) vs the 40M read's own 1.82/1.89/1.83/1.94, all within the +/-20% noise band the gate set; 0 new falls/terminations across all 24 episodes. But gait_valid REGRESSED hard: 3/24 total (0/6 det, 2/6 sto, 0/6 startjitter-det, 1/6 startjitter-sto) vs the 40M baseline's 10/24 -- det-mode now sacrifices TWO legs [1,4] in every single one of the 6 episodes (was single-leg leg4 at 40M). Reward is still climbing steeply (quarters 292->820->1360->1698, ep_rew_mean 1713) while fwd distance/speed held or improved (det fwd 3.68m identical across all 6 draws) -- the 08-21 rising-reward/bad-eval shape: freeprog reward keeps paying for distance from a leaner 4-leg gait, not pricing lost six-leg validity, so more budget widens the sacrifice rather than repairing it. This closes only the OFF arm's OWN retention question (slip/safety: HOLDS; gait-quality: DOES NOT HOLD, degrades further at depth). The paired ON arm's own cont10m (s11-acq1-cont10m) is still training this cycle -- the ON/OFF ratio comparison this pair was launched to answer stays open until it lands; do not average this OFF regression into the ON/OFF gap conclusion yet.

