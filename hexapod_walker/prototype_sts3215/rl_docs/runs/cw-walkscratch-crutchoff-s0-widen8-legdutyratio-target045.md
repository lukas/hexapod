# cw-walkscratch-crutchoff-s0-widen8-legdutyratio-target045

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-08T09:48:26+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widen8-acq1-legdutyratiofresh-guardfix1

**wandb_id**: s52ddexm

**hypothesis**: Plain English: does raising the leg-duty-ratio reward's balance target from 0.30 (the passing population's own p10 worst-leg ratio, STATUS.md 09-07 ~23:4x calibration) to 0.45 (closer to the passing population's median 0.537) more decisively suppress the widen8 composite's chronic front-pair leg sacrifice at the SAME fresh-init entry point and charge=150, without the slip/progress regression the 09-08 ~03:3x 10M-continuation study found from just running the SAME 0.30 dose longer? This is that closure's own nominated 'different dose/target' branch, not a re-run of the closed continued-charge study or a 3rd replication of the 0.30 dose.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY, 2M, same bar as the original legdutyratiofresh-guardfix1 canaries (gait_valid majority + 0 falls). Read jointly against the exact matched 0.30-dose guardfix1 sibling (identical seed/init-from/everything else, only target differs): PASS requires gait_valid equal-or-better AND slip_per_m/progress_ratio equal-or-better in a majority (>=3/4) of the 4 eval groups vs that sibling — per the 03:3x finding, a bare gait_valid uptick alongside worse slip/progress does not count. FAIL if chronic single-leg/pair sacrifice persists/worsens, or if slip/progress regress in a majority of groups vs the 0.30-dose sibling. Do not fund a further dose step or continuation off a FAIL; a PASS licenses one longer continuation to test durability, not an automatic dose escalation.

**verdict**: CANARY FAIL - MECHANISM: no net improvement over the matched 0.30-dose sibling; the 0.45-target dose does NOT license a further dose step. Own-arm gate required gait_valid AND slip/progress equal-or-better (mean, matching the 03:3x precedent's own metric) in >=3/4 of 4 groups vs the exact matched legdutyratiofresh-guardfix1 (0.30-dose) sibling. Read: walk/sto and walk_startjitter/det both improve (slip -2.7%/-0.7%, gait_valid held 6/6 both); walk/det shows the EXACT 03:3x-flagged pattern (gait_valid ticks up 5/6->6/6 by recovering ep0's sacrifice, but that same episode's slip jumps 21.4->27.3, group mean slip WORSENS +8.4%); walk_startjitter/sto regresses on both axes (slip +6.9%, progress -3.8%, same 2 chronic legs [0,5] unchanged). Net 2/4 groups clear both bars, short of the pre-registered >=3/4 majority -- gate NOT met. Video (contact sheet + walk_det_0 frame strip) shows a body barely translating in the worst episode, consistent with the numbers; no new pathology otherwise. Reward quarters fall hard [33,65,-1894,-6678], the family's known ep_len-growth artifact, not a fresh red flag. Per gate text, no further dose step or continuation follows. This closes the '0.30->0.45 different-dose/target' branch the 03:3x closure named as the one open follow-up: neither dose (0.30 nor 0.45) buys a real net gain, and both show the SAME single-episode gait_valid-for-slip trade in the same group -- the peer-relative duty-ratio charge appears to trade slip for duty-balance within an episode rather than genuinely fixing chronic sacrifice, independent of dose. s1 sibling still training elsewhere; whoever reads it closes the n=2 read.

