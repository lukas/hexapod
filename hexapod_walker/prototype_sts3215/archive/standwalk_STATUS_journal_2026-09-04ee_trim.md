# standwalk STATUS journal archive — 2026-09-04ee

VERBATIM copy of the Update block as it stood before the 09-04 ~08:2x
operator-directive cycle (fb_20260904T074505_6a3ac9: over_current
audit + eval_cmd_stress suite + transtress/cont canary pair).

Update, 2026-09-04 ~07:4x (**selomegaboost dose3.0/seed1 arm ALSO
reports CANARY FAIL - MECHANISM, 3rd of the 4-arm grid to close.
Only selomegaboost4p0-s1 remains (another cycle's territory); 3/3
triaged so far fail the identical sign-asymmetric pure-turn way.**)

`probe_turn_authority.py` run fresh this cycle on the run's own pod
(train-3) on the finished `...-selomegaboost3p0-s1` checkpoint (full
84-key non-train cfg-set replayed, 2 probe seeds averaged) vs the
matched `cap29-stdwalklo-hi-s1` (seed1) control: pure-turn wz_med
+0.203/-0.213 vs control +0.226/-0.247 — positive 9.9% (just under the
10% cap) but NEGATIVE 14.0% breaches it. Combined-tick (vx=0.08)
wz_med +0.095/-0.143 vs control +0.087/-0.142 — beats control on BOTH
signs this time (+9.2%/+0.9%), clearing that bar, but the pure-turn
cap breach alone is FAIL per the pre-registered gate regardless.
Training reward healthy (Q3 collapse to -252, clean recovery to 230
peak/172 final) — 08-21 ruling: mechanism failing on an aligned
reward with adequate budget, not a starved run. Same sign-asymmetric
erosion (negative sign hit harder) as dose3.0/seed0 and dose4.0/seed0.
1 sibling arm (selomegaboost4p0-s1) still awaiting triage (another
cycle's territory) — full axis-close needs all 4; see Next item 2.
Probe JSON: `logs/ckpt_eval/probe_turn_authority_
cap29_stdwalklohi_selomegaboost3p0_s1_combined_09-04.json`.
