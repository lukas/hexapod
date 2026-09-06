# cw-assistfade-rung2-harden-speedband-s0-v2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-06T14:31:24+00:00

**pod**: hexapod-mjx-train-4

**steps**: 8000000

**parent**: cw-assistfade-rung2-anchorfade-s0-reseed8m-gatefix

**wandb_id**: dydwknke

**hypothesis**: Rung 2 (anchor-fade) is now a 2-seed-confirmed ignition PASS (both -reseed8m-gatefix seeds, RL_LOG 09-06 14:0x/14:12) at a single pinned 0.06 m/s command; per the curriculum doc's own hardening ladder (speed band -> fixed headings -> command changes/stops -> yaw -> DR/pushes) the next unproven dimension is a WIDER SPEED BAND, not a new mechanism. Continues task-only PPO from the s0 gatefix 8M checkpoint with the BC anchor EXPLICITLY OFF (coef=0, anneal_gate=0 -- the anchor already fully annealed and its demonstrations were recorded at the old single speed, so re-enabling it here would re-run the anneal and confound the speed-band question), widening the per-episode command from a fixed 0.06 m/s point to a uniform 0.04-0.08 m/s band (still inside the previously-validated pinned-speed panel range, not an extrapolation). (v2: supersedes the same-named launch killed this cycle after respec silently carried over the source's un-zeroed anchor cfg.)

**gate**: PASS if the standard held-out det+sto gate (4 modes, each episode drawing its own per-episode speed from the widened band) clears: gait_valid majority (>=5/6) every mode, 0 falls/terminations, progress_ratio>=0.35 every mode, AND per-episode achieved speed tracks its own per-episode commanded speed (read off report.json episode rows: cmd_dist_m/10s vs speed_mean_m_s -- not clustered near the old 0.06 pace regardless of command). FAIL - COLLAPSE if gait_valid/falls regress from the ignition read at either band extreme (0.04 or 0.08) while the middle still passes -> retreat to a narrower band. FAIL - IGNORES-BAND if achieved speed stays flat near 0.06 regardless of the per-episode commanded value -> needs an explicit speed-tracking reward term before retry. slip/current recorded not gated (doc's own ignition-adjacent stage).

**verdict**: FAIL - IGNORES-BAND. Widening the pinned 0.06 m/s command to a uniform 0.04-0.08 m/s per-episode band and continuing task-only PPO (BC anchor off) from the rung-2 gatefix checkpoint: gait stays clean (gait_valid 6/6 every one of 4 modes, 0 falls/terminations all 24 episodes) but achieved speed does NOT track the command -- speed_mean_m_s clusters 0.037-0.039 m/s in every walk/det episode while cmd_dist_m/10s (the actual per-episode draw) spans 0.035-0.066 m/s, nearly 2x range. Two modes (walk/sto med 0.29, walk_startjitter/sto med 0.33) also miss the progress_ratio>=0.35 bar because achieved speed can't reach the higher end of the band. This is exactly the pre-registered FAIL-IGNORES-BAND clause, not FAIL-COLLAPSE (no gait/fall regression) and not the 08-21 rising-reward pattern (reward quarters 301.6/974.1/1327.3/1354.1 -- flattened, not genuinely still climbing). Root cause: the progress reward already normalizes by s_ref (r_prog=k_prog*min(along/s_ref,1.25)) so the incentive to match commanded speed exists in principle, but this continuation inherited the gatefix source's already-fully-annealed log_std (~-3.0, std 0.05) and re-applied --log-std-final -3.0/--log-std-anneal-frac 1.0 on top of that -- i.e. ZERO exploration boost for the whole 8M budget, so the policy never got to search for a genuinely different cadence per command; it just replayed its habitual single-speed gait. Not a reward-alignment bug requiring a new mechanism (the doc's own FAIL clause guessed 'needs a speed-tracking reward term' -- this is a training-schedule gap instead, per the documented --warm-log-std-override precedent for exactly this warm-start-doesn't-explore shape). Next: relaunch both seeds with --warm-log-std-override=-2.0 (anneal back to -3.0 over the same 8M) to test whether real exploration lets the policy learn genuine speed modulation. hardware-ready: no (band not obeyed). Evidence: logs/ckpt_eval/cw_assistfade_rung2_harden_speedband_s0_v2_gate/report.json, W&B dydwknke.

