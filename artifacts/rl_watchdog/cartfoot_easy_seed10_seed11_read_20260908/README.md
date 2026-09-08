# Exact EASY acquisition repeat-seed audit

The absence of several-fold Cartesian slip inflation repeats across all three fresh-init EASY seeds 7/10/11. This supports acquisition viability at the tested Cartesian dose; it does not establish a general slip benefit, consistent deterministic six-leg gait, or current1x capability.

| Seed | Group | ON/OFF gait | ON/OFF mean slip/m | Ratio | ON/OFF mean progress | ON/OFF median forward m/s |
|---|---|---:|---:|---:|---:|---:|
| 10 | walk/det | 0/6 vs 0/6 | 2.611/3.046 | 0.857 | 3.068/2.818 | 0.1830/0.1657 |
| 10 | walk/sto | 6/6 vs 6/6 | 3.351/3.339 | 1.004 | 2.532/2.576 | 0.1499/0.1513 |
| 10 | walk_startjitter/det | 0/6 vs 0/6 | 2.681/2.954 | 0.907 | 3.075/2.931 | 0.1799/0.1653 |
| 10 | walk_startjitter/sto | 6/6 vs 6/6 | 3.208/3.277 | 0.979 | 2.636/2.679 | 0.1522/0.1557 |
| 11 | walk/det | 6/6 vs 0/6 | 2.894/3.025 | 0.957 | 2.960/2.714 | 0.1668/0.1614 |
| 11 | walk/sto | 6/6 vs 6/6 | 3.356/3.541 | 0.948 | 2.594/2.477 | 0.1503/0.1439 |
| 11 | walk_startjitter/det | 5/6 vs 0/6 | 2.812/2.927 | 0.961 | 3.060/2.816 | 0.1794/0.1695 |
| 11 | walk_startjitter/sto | 6/6 vs 6/6 | 3.385/3.325 | 1.018 | 2.598/2.601 | 0.1538/0.1522 |

Zero terminations across each of the four 24-episode reports. Seed 10 gait totals 12/24 ON and 12/24 OFF; seed 11 totals 23/24 ON and 12/24 OFF. These totals include repeated nominal deterministic episodes, not independent trials.

Both arms meet their own numeric acquisition criterion (>=0.03 m/s median net forward in walk/det or sto and zero det falls). ON23/24 versus OFF12/24 gait is a real descriptive difference, but gait was not a separate hardening bar in this registered criterion.

Both arms walk with zero falls and stochastic gait12/12; both deterministic panels have gait0/12. Their registered PASS-BAND invokes gait_valid/no-falls/slip comparable to established base-family walking, without a numeric pass fraction. Thus movement/slip-band parity is supported, while clean deterministic six-leg qualification is not. Preserve this qualification alongside the owner recorded ON ACQ PASS - PARITY (BAND-MATCH, non-blocking det quirk); this audit does not mutate that verdict.

Registered criteria (verbatim from native ledger reads):

- s10on: PASS-BAND if it reaches gait_valid/no-falls/slip comparable to the base family's own established PASS band (base-s0..s4) on the same fixed-forward walk panel -- report slip/m specifically vs that band. FAIL if it cannot reach walking at all by 40M while sibling base-family seeds all could. Per the 08-21 ruling, judge on reward trend + eval together, not reward alone.
- s10off: PASS-BAND if it reaches gait_valid/no-falls/slip comparable to the established base-family PASS band (base-s0..s4) on the fixed-forward walk panel. Read paired against base-cartfoot-fresh-s10-c1b at the same cumulative depth: this completes the seed-10 half of the n>=3 fresh-init ON/OFF cohort. FAIL if it cannot reach walking at all by 40M despite sibling base-family seeds all reaching it. Per the 08-21 ruling, judge on reward trend + eval together.
- s11on: ACQUISITION: >=0.03 m/s median net forward in >=1 of walk/det,sto (0 falls in det), read together with offctrl-s11-acq1 at the SAME budget. PASS/CONTINUE per the 08-21 ruling if reward is still rising; slip/m vs the matched OFF sibling is the headline comparison, not a hardening bar.
- s11off: ACQUISITION: >=0.03 m/s median net forward in >=1 of walk/det,sto (0 falls in det), read together with cartfoot-freshinit-c1-s11-acq1 at the SAME budget. This is the matched control -- if it itself drifts/fails the acquisition bar, read the ON/OFF pair as inconclusive rather than crediting/blaming the Cartesian mechanism.

Pairing and limits:

- Each pair has the same seed, 2M fresh-init parents without --init-from, own-checkpoint 40M continuation, and only three Cartesian cfg-set differences. Seed 10 parent ledger names base-s0 as recipe parent but command has no --init-from: it is not mature-checkpoint transfer.
- All four final W&B steps are read explicitly; do not silently rewrite 40M requested continuation to the hypothesis narrative +38M.
- Reported randomization matches 24/24 within each pair and jitter summaries match 12/12. Full offset vectors and hidden RNG/state are absent, so this is reported-draw pairing, not byte-exact full-state proof.
- Six nominal deterministic repetitions are one condition, not six independent samples. Only three training seeds total; no inferential significance or pooled144-episode claim.
- Training commits differ but compared prototype deltas contain no training simulator or config source changes. This does not independently hash uncommitted live pod source or every loaded asset.
- All gates use the EASY 3x-torque, no-latency/deadband/sensor-noise, DR 0, fixed-forward 0.06m/s, 100Hz, mesh_mjx 0-mesh91-geom 4.80573kg recipe. Progress ratios 2.48–3.07 reflect overspeed, not tracking qualification.
- No session/hardening reports or old retrofit1.5x/3x slip criteria enter the acquisition interpretation.

Existing gate strips were viewed. All four existing deterministic contact strips were viewed. Bodies stay upright across shown frames with translation and changing leg poses; the reports quantify sacrificed-leg failures. No clean deterministic six-leg or measured slip claim is inferred from still images.

The repeated EASY result leaves a meaningful orthogonal question of torque dependence, so a predeclared matched fixed 1x test remains scientifically justified. Do not claim readiness at 1x, or expand EASY training simply because numerical acquisition passed. Retain the active owners and existing bounded continuation decisions.

Exact reports, ledger/parent snapshots, cached metrics, native video path metadata, image hashes and repeatable analysis are stored alongside this note. No owner verdict, code, launch or active process was changed.
