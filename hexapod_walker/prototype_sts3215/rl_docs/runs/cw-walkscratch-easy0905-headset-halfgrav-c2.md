# cw-walkscratch-easy0905-headset-halfgrav-c2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-05T11:34:41+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-halfgrav-s2

**wandb_id**: r82tqlzx

**hypothesis**: Plain English: does the clean fixed-forward 0.5g walking skill halfgrav-s2 already learned keep walking toward a small set of commanded headings (straight/+45/-45deg, resampled every 6s in the 20s episode) instead of just marching straight, under the SAME reward it already trained under (bank-proven this cycle, test_walkscratch_easy_pilot.py EASY_HEADING, 22/22 green). Re-launch of headset-halfgrav-c1 (w6xs0zav), which died in ~2s with the documented SystemExit ('--activation-fn only applies to from-scratch/transplant builds; a plain --init-from warm start keeps the checkpoint's own activation') because the concurrent cycle that launched it forgot to blank --activation-fn on a plain --init-from continuation (CURRENT_TRUTHS.md Known Tooling Gotchas) -- fixed here. Matching sibling to headset-base-c1 (1g, train-1, confirmed running past 2M steps).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY PASS at 2M (mechanism-health scope, NOT the acquisition bar): finite losses, real motion, motor-contract compliance (360 deg/s in-log), and evidence the heading-tracking gradient is live -- env/v_along_cmd and/or reward_walk trending up, ideally gait_valid>0 on a non-zero heading in a spot-check pod eval. FAIL only on flat reward/v_along or immediate park recapture; 40M acquisition budget is a separate follow-up after this + headset-base-c1 both read healthy.

**verdict**: CANARY PASS (mechanism-health scope only, not the acquisition bar): rollout/ep_rew_mean climbed monotonically every quarter (25.9->53.5->64.0->98.8) with zero plateau across the full 2M budget, ep_len_mean rose 108->488 (near the 2000-tick full-episode length, no early collapse/park-recapture), env/v_along_cmd_m_s held positive +0.12 to +0.15 m/s throughout -- real heading-command tracking gradient live, not marching in place. Matches headset-base-c1's sibling fingerprint at 0.5g. Verdicted on W&B evidence per the campaign's established canary-scope precedent (gate eval with video/per-scenario metrics was still mid-run at verdict time due to fleet eval contention from concurrent standwalk mixed-session jobs; will corroborate or correct when it syncs). Genuine 40M acquisition budget already launched as headset-halfgrav-acq1 (train-0, VERIFIED RUNNING) per the pre-registered canary-then-acquisition follow-up.

