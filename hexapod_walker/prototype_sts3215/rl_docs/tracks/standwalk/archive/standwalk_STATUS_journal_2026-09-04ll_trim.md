# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-04 ~17:0x: **Steering branch (Next#2) FULLY RESOLVED,
both seeds — comparator noise, not a real lever effect.** `cont-b`/
`cont-c` (2nd/3rd zero-lever seed0 continuations) verdicted PASS; n=3
seed0 band: pt 0.157-0.200, cb_pos 0.121-0.132, cb_neg 0.152-0.190.
(a) the seed0 "9/10 lever FAIL" figure doesn't survive: `cont-b`/
`cont-c` (themselves zero-lever) also FAIL vs `cont` single-control,
proving that comparator invalid; band-scored, only 1/10 cells
(`yawarm1p5`) wins both cb signs, matching seed1. (b) seed0 cb_neg
does NOT collapse (0.152-0.190, tracks frozen-parent-s0 0.170) unlike
seed1's collapsed 0.120-0.138 — that erosion is SEED1-SPECIFIC.
Binding: frozen parents stay the best steering checkpoints on both
seeds; NO lever acquisition. Manifest: `logs/ckpt_eval/
rescore_turn_authority_09-04/manifest_n4.json`.

Also this cycle: **Next#1 tooling landed + first read INCONCLUSIVE at
n=3.** `run_episode` persists the per-episode DR draw
(`ep["randomization"]`, additive/bit-exact-off when off) + new
`audit_dr_hold_correlate.py` (fired-vs-clean median/std-mean-diff per
field). Tests green; snapshotted `exp/standwalk-dr-draw-logging-09-04`.
Matched-72 own-DR pass on the k=8 checkpoint (train-5): only 3/36
fire `hold_min_load` (matches known 8.3%), spread across 3 different
buckets/start_kinds — not one mode. No DR field cleanly separates at
n=3 (top hit `zero_bias_max_deg` d=-1.05, not trustworthy). Launched
`--n 20` (~10x fires expected) on train-5, `..._cmdstress_n20/` — new
Next item 1.

Prior updates (09-04 ~13:2x..~16:3x) archived verbatim in `archive/
standwalk_STATUS_journal_2026-09-04{hh,jj,kk}_trim.md`.
