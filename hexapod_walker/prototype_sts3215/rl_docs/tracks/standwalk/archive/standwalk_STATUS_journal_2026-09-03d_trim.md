# standwalk STATUS journal archive — 2026-09-03d (trimmed from top of STATUS.md)

Update, 2026-09-03 ~04:0x (idle-kick, item 0 STILL mid-flight on
train-6/7, pace unchanged): closed the "tangle-spread physics" item
flagged last entry -- it was a PROBE bug, not a sim bug. The prior
"tangle_60->70 pad_spread genuinely DECREASES" claim came from a repro
script that skipped `conftest.py`'s `HEXAPOD_MODEL_SOURCE=primitive`
pin, measuring on `mesh` instead. Correctly-pinned, the true gap is
real (~5mm) but smaller than one seed's noise (std 9-48mm) -- the
bank's n=3 mean was 2 unlucky draws, not a reversal (8/8 clean
monotonic resamples at N=24-30 seeds). Fix: pad-spread now averages
its own 30-seed sample (shared 3-seed `SEEDS` untouched elsewhere);
margin 1.5->0.5mm to match. Verified 4/4 stable reruns, `-k recover`
30/33 (3 pre-existing unrelated npz-migration fails). Test-only, no
cfg touched. Fresh full-suite regression running for a future cycle
(`/tmp/full_after_tanglefix_0903.log`; pre-fix baseline 40 failed/255
passed at ec7bf19f). Open items left: `test_getup_honest_ordering`
(reward-design gap, no arm queued) and ~16-18 `walkcurr_pf` reds
(RETIRED track). Snapshotted+pushed. Full derivation: OPERATOR_
QUESTIONS.md.
