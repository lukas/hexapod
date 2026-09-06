# cw-walkscratch-easy0905-headset-crossgrav-widen2c1-irrfwd-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T04:53:29+00:00

**pod**: hexapod-mjx-train-8

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-widen2c1-irrfwd-c1

**wandb_id**: qiuquuie

**hypothesis**: Plain English: forward-composing the irr-timing jitter axis onto the widen2c1 crossgrav champion (already transferred to full 1g) CANARY PASSed at 2M (gait_valid 21/24, no chronic leg pattern, but 1 genuine fall + slower/noisier than the medhead-based siblings). This is the acquisition-scale (40M) confirmation matching the medhead-{widenfwd,irrfwd}-c1-acq1 precedent (both held clean at 40M): does this harder/slower 2nd base champion's composed gait hold, entrench, or resolve its single fall/noise under a full training budget?

**gate**: ACQ PASS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with no chronic (<0.10-duty every episode) single-leg sacrifice at 40M, matching or improving the 2M canary's 21/24 read, and no MORE than the canary's 1 fall (ideally 0). ACQ FAIL if walk/det or walk/sto regresses to majority failure, the leg[1,4]-style chronic-park fingerprint emerges/hardens, or falls increase under longer 1g exposure. ACQ CONTINUE if reward is still climbing with borderline (not hard-park) duty, per the 08-21 ruling.

**verdict**: ACQ PASS (40M): the widen2c1-irrfwd-c1 composition (2M canary was 21/24 gait_valid + 1 fall) HOLDS at 21/24 and IMPROVES on the fall count and every locomotion-quality metric at 40M. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_widen2c1_irrfwd_c1_acq1_gate/report.json (pulled by hand off hexapod-mjx-train-8 after a websocket-disconnect prestage failure — SYNCED rc=1 masked a fully-computed, already-complete gate eval sitting on the pod since 06:35, same transient this campaign has hit before) vs the parent's own logs/ckpt_eval/..._widen2c1_irrfwd_c1_gate/report.json: gait_valid 5/6+6/6+5/6+5/6=21/24 both canary and ACQ (identical per-mode split); falls 0/24 at ACQ vs 1/24 at canary (the canary's walk_startjitter/sto/0 tilt_roll fall resolved into a non-fatal leg flag at a DIFFERENT episode, sto/5); the two non-fall single-leg flags reproduce at the IDENTICAL episode+leg (walk/det/3->leg5, walk_startjitter/det/4->leg1) as the canary, i.e. the same pre-existing signature, not a new or spreading pathology; slip/m dropped across all 4 modes (det 5.69->4.02, sto 8.30->4.86, startjitter/det 5.36->4.58, startjitter/sto 6.13->4.61 median) and progress_ratio rose in all 4 (1.13->1.86, 0.93->1.58, 1.30->1.50, 1.18->1.67). Video-confirmed clean six-leg cycling with real body translation in both a clean episode (walk_det_0) and both flagged episodes (walk_det_3, walk_startjitter_det_4, walk_startjitter_sto_5) — no drag/freeze/collapse. Why: matches the medhead-widenfwd/irrfwd-c1-acq1 precedent that composition arms clean at canary tend to hold or improve at ACQ scale on this campaign's family, extending it to the harder/slower widen2c1 base champion. Next: queue a cont40m endurance continuation (this campaign's standing rule: clean ACQ PASSes without an endurance read are the current refill priority).

