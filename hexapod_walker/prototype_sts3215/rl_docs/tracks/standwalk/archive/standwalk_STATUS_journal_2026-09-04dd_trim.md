# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-04 ~07:3x (**selomegaboost dose4.0/seed0 arm ALSO
reports CANARY FAIL - MECHANISM, 2nd of the 4-arm grid to close.
Raising the dose fixed the OTHER bar (combined-tick) but not the
pure-turn erosion — confirms the erosion is dose-independent.**)

`probe_turn_authority.py` on the finished `...-selomegaboost4p0`
checkpoint (full 84-key non-train cfg-set replayed on the run's own
pod, 2 probe seeds) vs the matched `cap29-stdwalklo-hi` seed0/seed1
controls: pure-turn wz_med +0.212/-0.194 (s0), +0.219/-0.200 (s1) vs
controls +0.223/-0.250, +0.226/-0.247 — negative-sign regression
22.4%/19.0%, BOTH seeds breaching the 10% cap (positive sign fine,
4.9%/3.1%). Combined-tick (vx=0.08) +0.120/-0.171 (s0), +0.114/-0.163
(s1) DOES beat control both signs this time (s0-negative barely) —
dose 4.0 fixed dose3.0's positive-sign shortfall — but the pure-turn
cap breach alone is FAIL per the pre-registered gate regardless.
Training reward healthy (Q3 collapse to -258, clean recovery to 243.9
final) — 08-21 ruling: mechanism failing on an aligned reward with
adequate budget, not a starved run. Same sign-asymmetric erosion as
every prior lever, now shown dose-independent (3.0 and 4.0 both fail
the same way). 2 sibling arms (-4p0-s1, -3p0-s1) still awaiting triage
(another cycle's territory) — full axis-close needs all 4, see Next
item 2. Probe JSON: `logs/ckpt_eval/probe_turn_authority_
cap29_stdwalklohi_selomegaboost4p0_combined_09-04.json`.

Prior banner (dose3.0 FAIL) moved to `archive/standwalk_STATUS_
journal_2026-09-04cc_trim.md`.
