# standwalk STATUS journal archive — 2026-09-02 ~21:3x block (moved verbatim 2026-09-02 ~22:2x)

# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-02 ~21:3x: idle-kick (item 0's read still mid-flight,
confirmed live on train-6/7) drained the semantics-bank dig-in the
09-02 ~19:1x/20:1x note flagged as next: 6/8 standwalk-relevant
failures (stopcurrent, rise_rock, hold x2) were stale test-fixture
calibrations, fixed+verified. The other 2 (`trans_drag`) are a REAL
production bug: `trans_drag_mm`/`k_drag_loaded`'s per-tick slip
deadband (hardcoded `slip > 0.0005` m, `sim_env.py`/`walk_task.py`)
was calibrated at the pre-08-24 default 25 Hz control rate and is now
4x too loose at the current 100 Hz default (12.5mm/s intended floor
read as 50mm/s) — **every current standwalk arm's live
`k_drag_loaded=10.0`/`k_drag_stance=8000.0` inherits this**, plausibly
under-pricing slow persistent slip ("paddle-creep") and relevant to
the still-open steering/slip gap (item 1). NOT patched this cycle
(shared training default, needs a full-bank regression pass before
touching); full writeup + proposed dt-scaled fix in
`OPERATOR_QUESTIONS.md` 2026-09-02 ~21:0x-21:3x entry — **try this
FIRST** before designing a new steering mechanism for item 1.
`getup_honest_ordering` traced to a genuine income-vs-effort balance
gap (getup isn't in any live arm's mode mix, left for later).
Snapshotted+pushed.
