# standwalk STATUS journal archive — 2026-09-03p

Verbatim archive of the top "Update" block from `STATUS.md` (candidate
(ii) build + 4-arm launch announcement) before the 09-03 ~21:1x
4/4-FAIL close replaced it at the top. Do not act on this as current
state — read STATUS.md's current top Update instead.

---

Update, 2026-09-03 ~20:2x (**Next item 2 candidate (ii) BUILT +
LAUNCHED: `reward.walk_yaw_combined_boost` harness + 4-arm canary
batch now RUNNING.**)

Item 2's own prescription ("pick one, build its validation/bank
harness, THEN launch a matched canary") is done for candidate (ii).
Built `reward.walk_yaw_combined_boost` (`walk_task.py`, default
1.0=bit-exact identity, mirrors `train.bc_anchor_teacher_omega_
boost`'s own gating): a MULTIPLIER, not a gate, applied only to the
existing `k_walk_yaw` kernel income on genuine combined ticks (linear
speed AND yaw rate both commanded) — corrected mid-build: an earlier
draft assumed (from `probe_turn_authority.py`'s stale docstring) that
this family trains with `k_walk_yaw=0`; the ledger's own cfg for
`cap29-stdwalklo-hi` shows `k_walk_yaw=1.0` applied to EVERY walk
tick already, so a zeroing GATE (the first design) would have
REMOVED supervision from the already-working pure-turn behavior
instead of adding it where degraded — a boost multiplier is the
correct surgical lever. Semantics bank
(`test_task_semantics.py`, "STANDWALK combined-tick-targeted yaw term
bank"): pins the measured sign-asymmetric exploit (positive combined
wz retains ~44% of pure-turn magnitude, negative ~68%, from the
cap29-stdwalklo-hi comparator) as a scripted twin the CURRENT
(boost=1.0) stack cannot distinguish from a symmetric-good twin
(asym/sym price within ~1% of each other), then proves boost=6.0
separates them by >600pts/ep — the mechanism has real gradient before
any GPU spend. 8 new/modified tests, all green (4 gate-mechanics +
the exploit-pinning test, plus `_steer_rollout` gained `return_terms`/
`tail_only`); full `-k "steer or yaw or turn or walkteach"` + all 101
`test_bc_anchor.py` tests rerun green except one PRE-EXISTING failure
(`test_kernel_yaw_ema_separates_accurate_tracking_from_undershoot`,
confirmed failing identically on unmodified `main` — not caused by
this change, not fixed this cycle). Also applied item-2 rider (a):
new arms set `safety.max_current_a=2.5` (below the measured 2.64A
model ceiling; the sibling canaries' `2.9` silently disabled
`over_current`). Snapshot `0b15f140`
(`exp/standwalk-combined-yaw-boost-lever-09-03`).

**LAUNCHED**: 2-dose x 2-seed canary batch, respec'd from the matched
comparators `cap29-stdwalklo-hi{,-s1}` (identical recipe minus the new
flag): `cap29-stdwalklohi-yawboost{3p0,6p0}{,-s1}`, all 4 VERIFIED
RUNNING (train-1/2/3/10). One infra snag hit 3/4 arms (`tar: ...
linux_control/vision_ui: Cannot open: File exists` on train-1/2/3,
the same AprilTag-submodule-extraction stale-directory class noted in
the 09-03 17:5x omegaboost launch) — cleared via `kubectl exec ... rm
-rf .../vision_ui` on the affected pods, then requeued; all 4 now
running clean. NEXT CYCLE: read the 4-cell canary
(`probe_turn_authority.py --vx-cmds` combined read vs the pre-
registered gate) — do NOT trust the raw final-step reward number
alone (rider c: the whole cap29 family, incl. both combskip seeds,
showed a Q3 training-reward collapse).

