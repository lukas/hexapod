# standwalk STATUS journal archive — 2026-09-03j (verbatim, pre-semantics-bank)

Update, 2026-09-03 ~14:2x: **seed1 (`yawdensity-canary-s1`) VERDICTED
CANARY FAIL - MECHANISM; the rise `over_current` DIG-IN is RESOLVED:
GENUINE lineage rise-stall fragility, NOT a mode_seq-mixing instrument
defect — the redesign escalation (Next item 2) is UNBLOCKED.**
Steering: seed1 is strictly worse than seed0 (dir_err_med 44.7-45.5deg
vs the 38-41deg FAIL band; course_err_1s 18.8-24.8deg; sto slip
11.1-14.1) — seed-robust refutation of the structural branch. Dig-in
evidence: (a) isolated rise-only DR-0 read (no mode_seq mixing,
`logs/ckpt_eval/yawdensity_s1_riseAB_cap25own`, train-5) reproduces the
falls HARDER than the mixed gate — 6/8 det, 8/8 sto `over_current`,
killing the instrument-defect hypothesis; (b) cap-2.9 counterfactual
(`.../yawdensity_s1_riseAB_cap29cf`): 0/16 trips but 11/16 episodes
stall 45-62 mm BELOW rise target with servos torque-saturated 8-23 s —
behavior broken regardless of cap (video: freezes mid-crouch fighting
isometrically at the 2.64 A ceiling, then collapses at 2.5 / lurches
over-extended at 2.9); (c) root cause: family-wide Q3 training-reward
collapse (s1 quarters [24,29,-200,14] last 58.8; s0 [22,53,-188,72]
last 177.2; ancestor [54,44,-212,-22] last 66) — s1's checkpoint sits
at family-TYPICAL weak recovery (s0 is the outlier), and the ancestor's
own gate already showed the same rise trips (1/6 det, 2/6 sto). So
seed0's clean count = recovery-depth luck, not health. **TWO NEW
INSTRUMENT/CONFIG FACTS (binding for family comparisons):** (1)
name-misnomer — both yawdensity seeds respec'd from the pre-cap29
`gradclip0p15-canary` ancestor and train+eval WITHOUT
`safety.max_current_a=2.9` or the stdwalklohi speed keys (cap =
SafetyLayer default 2.5, walk_speed fixed 0.08); (2) sim current =
`min(|torque|*1.2, 3.0)` with the 2.2 N·m axes' ceiling at 2.64 A, so
at cap 2.9 the `over_current` trip is UNREACHABLE on standard axes —
the true-cap29 siblings' "zero over_current falls" are partly
trip-blind and rise stalls there hide as silent height misses. The
reward-mechanism redesign must therefore ALSO price rise-stall
(saturated isometric freeze is currently reward-survivable) and fix
current-cap semantics (a trip threshold above the model ceiling is a
disabled trip). Evidence: ledger verdict on `yawdensity-canary-s1`.

Previous update, 2026-09-03 ~13:3x: **item 1 seed0 (`yawdensity-canary`)
VERDICTED CANARY FAIL - MECHANISM; seed1 stays the concurrent cycle's
open DIG-IN (below) — do not let this close the family alone.**
Same walk-only steering read (n=16, dr0/ownDR x det/sto, no-video,
harsh eval-diet override): walk/det dir_err_mean_med 40.65deg (flat
inside the 38-41deg FAIL band); course_err_1s_med_med 23.49deg
(dr0)/18.88deg (ownDR) — 1.5-2.4x WORSE than the FAIL band's own
9.6-12.6deg, not better; slip_per_m_med 4.32-4.47, above the ~3.8
ceiling. `probe_turn_authority`: clean (wz_med 0.18-0.23 rad/s, zero
probe falls) — the miss is steering-while-walking-forward specifically,
not a general turn regression. gait_valid 16/16 in 3/4 subgroups
(15/16 in the 4th). This clears the gate's own FAIL branch ("worse
than the ancestor on any axis") on the primary dir/course/slip
metrics ALONE — that call does not depend on the termination question
below, so seed0 is verdicted now rather than waiting on seed1's
reconciliation. **Caveat carried forward, not resolved**: seed0's
own-DR-det group has the SAME failure shape seed1 shows at high rate
(one `over_current` term at t=17.77 with `seq_end_seg_mode=rise`) —
at seed0's low incidence (1/16, plus one unrelated late `hold_min_load`
in the hold segment matching prior baseline noise) this reads as
noise, but seed1's 7-12/16 rate in EVERY subgroup says it may be a
real (dose- or seed-dependent) rise-phase fragility inside the mixed
walk->rise mode_seq episode under the forced harsh diet, possibly an
INSTRUMENT defect (the canary-family gate's mode_seq mixing), not a
checkpoint property. Do NOT treat seed0's clean-looking termination
count as proof the anomaly is seed1-only until the reconciliation
item below (isolated per-mode rise-only gate/owncfg, no mode_seq
mixing) actually reads clean on seed0 too. **Verdict on the
STRUCTURAL branch stands regardless**: walk_yaw_zero_frac (0.5->0.2)
does not close the steering gap on seed0, matching the diet-rate
branch's own closure — both pre-registered branches of the track's
turn-authority fork are refuted on seed0. The FAMILY-WIDE escalation
call (full reward-mechanism redesign) stays open pending seed1's
termination-anomaly reconciliation, per the concurrent cycle's own
Next item 1 below — do not launch a redesign arm until that resolves,
since if it's an instrument defect the "escalate" conclusion itself
would be built on a miscalibrated gate. Evidence: ledger verdict on
`yawdensity-canary`, `logs/ckpt_eval/standwalk_yawdensity_canary_
walkcheck/*/report.json`, `logs/ckpt_eval/probe_turn_authority_
yawdensity_canary.json`.

Previous update, 2026-09-03 ~13:2x: **item 1 (yawdensity-canary) built
+ read both seeds — FLAGGED DIG-IN, NOT verdicted (seed1 side).** `probe_turn_authority`:
clean both seeds (wz_med 0.18-0.23 rad/s, zero probe falls). Walk-only
steering read (n=16, dr0/ownDR x det/sto, no-video, same instrument as
the diet-family canaries): det dir_err_med 40.7-45.5deg (vs the
38-41deg FAIL band)/slip 3.4-4.5 — ordinary continuation of "lever
doesn't move steering." But **seed1 shows a severe, seed-asymmetric
NEW failure**: 7-12/16 `over_current` terms in EVERY subgroup incl.
dr0-det (cleanest condition; seed0's dr0-det is 0/16) — and every
termination's `seq_end_seg_mode` is `"rise"`, not `"walk"` (fails
~15-17s in, deep into the mixed walk->lower->rise->hold episode, after
walk metrics already captured). Sto numbers also diverge wildly from
every prior canary here: dir_err 73-77deg/slip 11-18 (det/sto used to
track closely). Two unresolved hypotheses: (a) seed1 drew a genuinely
fragile RISE sub-skill, orthogonal to the tested lever (seed noise);
(b) the forced harsh eval diet degrades the walk segment enough that
RISE inherits a compromised state (implicates the mixed-episode gate
INSTRUMENT, not the checkpoint). The gate's own FAIL text is literally
satisfied ("new own-DR falls appear") but closing the whole lever
family + escalating to a full reward-mechanism change on an
unreconciled, seed-asymmetric, wrong-mode failure would be premature —
left unverdicted. The standard prestage gate/owncfg (isolated per-mode
rollouts, no mode_seq mixing) are independently computing on train-3/
train-4 and will give a clean rise-alone read to reconcile (a) vs (b).
Full numbers + per-subgroup n_term breakdown: ledger DIG-IN note on
`yawdensity-canary-s1`. Artifacts: `logs/ckpt_eval/standwalk_
yawdensity_canary{,_s1}_walkcheck/*/report.json`, `logs/ckpt_eval/
probe_turn_authority_yawdensity_canary{,_s1}.json`.

Earlier updates (resamplematch-mild-canary close, item 0 close,
resamplematch/turndiet-s1 diet-match refutation, joint-frame-stamp fix,
fast-read, getup/q0/hold/joint-frame-v2 fixes, 09-02 merge-recovery)
moved VERBATIM to `standwalk_STATUS_journal_2026-09-03i_trim.md`
+ `2026-09-03{a..h}_trim.md` + `2026-09-02{f,h}_trim.md`.
