# Independent EASY seed 7 acquisition read

Both seed 7 arms meet their registered movement/no-det-fall acquisition criterion. The predicted 3–10x Cartesian slip inflation is absent in this matched EASY seed 7 comparison; ON mean slip is 1.2–5.6% lower across the four groups. This is descriptive acquisition parity, not a demonstrated general Cartesian advantage or current1x readiness.

| Group | ON/OFF gait | ON/OFF mean slip per m | Slip ratio | ON/OFF mean progress | ON/OFF median net forward m/s |
|---|---:|---:|---:|---:|---:|
| walk/det | 6/6 vs 6/6 | 2.791/2.826 | 0.988 | 3.258/3.155 | 0.1845/0.1879 |
| walk/sto | 6/6 vs 6/6 | 3.220/3.412 | 0.944 | 2.744/2.608 | 0.1580/0.1522 |
| walk_startjitter/det | 5/6 vs 1/6 | 2.789/2.850 | 0.979 | 3.325/3.090 | 0.1921/0.1844 |
| walk_startjitter/sto | 6/6 vs 6/6 | 3.095/3.257 | 0.950 | 2.854/2.751 | 0.1600/0.1580 |

Both arms: zero terminations in all 24 episodes. Gait totals ON 23/24 vs OFF 19/24, driven by deterministic start-jitter 5/6 vs 1/6. Failed gait reports identify sacrificed leg 4 (plus leg 1 in one OFF episode).

Exact registered seed 7 gate: ACQUISITION: >=0.03 m/s median net forward in >=1 of walk/det,sto (0 falls in det), read together with offctrl-s7-acq1 at the SAME budget. PASS/CONTINUE per the 08-21 ruling if reward is still rising; slip/m vs the matched OFF sibling is the headline comparison, not a hardening bar.

Pairing: identical report metadata; same training seed 7 and respective own 2M canary checkpoints, then the same 40M continuation budget. Only effective cfg-set differences are the three Cartesian box extents; all 24 randomization summaries and all 12 jitter summaries match. See summary.json for exact fields and per-episode jitter summaries.

Visual check: Both existing ten-frame deterministic gate contact strips show upright bodies and changing leg poses with visible net translation. No shown collapse/tip. Similar qualitative appearance; no visual superiority assertion.

- EASY recipe: fixed forward 0.06 m/s, 3x torque, no latency/deadband/sensor noise, DR scale0, mesh_mjx twin (0 meshes/91 geoms). No current1x/fullmesh/hardware claim.
- Each nominal deterministic group repeats one condition six times, not six independent seeds. Only one matched training-seed acquisition pair is assessed here.
- All 24 reported randomization payloads and all 12 start-jitter summaries match between arms. Summaries omit full reset offset vectors and hidden RNG/state, so this does not prove byte-exact full-state or every RNG draw parity. Own ON/OFF checkpoints differ by design.
- Progress ratios 2.61–3.32 indicate acquisition with substantial overspeed relative to the fixed reference, not speed tracking qualification.
- No generic hardening slip threshold or old retrofit 1.5x/3x rule is imported: the seed 7 ledger explicitly makes slip the comparison headline, not its acquisition gate. The expected OFF5–6/m band was not a lower bound.
- A movement gate pass does not independently authorize a further continuation; reward trajectory and next bounded hypothesis belong to active owner073301.

Seed 10 c1b: separate own gate is still computing (PID 2949171, recent artifacts); no gate conclusion or substitution from session reports. Its older-family PASS-BAND criterion is preserved verbatim in summary.json.
