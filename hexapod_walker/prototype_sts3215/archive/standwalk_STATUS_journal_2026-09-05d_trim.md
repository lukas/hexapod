# standwalk STATUS journal archive — 2026-09-05d

Verbatim prior "Update" block, superseded by the 09-05 ~06:1x update
(the multi-teacher 4/4 close is fully summarized in that update + Next
item 1; this is the full seed1-read text as originally recorded).

---

Update, 2026-09-05 ~05:5x: **phase-scheduled multi-teacher canary,
ALL 4/4 ARMS IN — ALL FAIL. Reward/supervision-side lever axis for
standwalk items 1/2 is CLOSED FOR GOOD (~24 arms total).** Seed1 half
(`multiteach-b05-s1`/`-b10-s1`) read this cycle via `probe_turn_
authority.py` (identical full 84-key cfg replayed on-pod, wz-cmds
0.25/-0.25 x vx-cmds 0/0.08, probe-seeds 0+1 avg) vs this run's own
pre-registered seed1 control (pure-turn +0.226/-0.247, combined
+0.086/-0.142): b05-s1 pure-turn +0.216/-0.201 (neg -18.6%, past the
10% cap; combined neg -2.7% also fails the beat-both-signs clause);
b10-s1 (full dose) pure-turn +0.179/-0.164 (BOTH signs regress,
-21.0%/-33.8% — worse than half dose, matching the seed0 dose-
response direction). No falls in either probe (fell:false, all 16
rows across both arms). Matches the seed0 half (verdicted 05:40/05:41,
same cycle): b05 -21%/-33%, b10 -48%/-39% pure-turn regression, both
failing combined-tick beat-both-signs. **4/4 cells fail identically —
phasing the aggressive pure-turn target in late does not protect the
safe demo's own pure-turn magnitude at any tested dose/seed.** Full
JSON: `logs/ckpt_eval/probe_turn_authority_cap29_stdwalklohi_
multiteach_b{05,10}{,_s1}_combined_09-05.json`.

No further static-or-scheduled reweight/rescale of the combined-tick
BC-anchor target — every variant tried (`combined_skip`, `combined_
dose`, `yaw_arm_scale`, `omega_boost`, `selective_omega_boost`,
phase-scheduled multi-teacher) fails the identical negative-sign-hit-
harder pure-turn regression. Item 2(b) (renegotiate the DONE gate's
numeric bar) was independently investigated and REFUTED 09-05 04:0x:
`probe_dir_floor.py --resample-s` extension shows the scripted
teacher's own dir_err_med floor stays 8.6-9.2deg even under 20
full-circle heading resamples over 60s — the ~40deg/2.9-slip caps are
real, achievable targets, not a miscalibrated proxy.
