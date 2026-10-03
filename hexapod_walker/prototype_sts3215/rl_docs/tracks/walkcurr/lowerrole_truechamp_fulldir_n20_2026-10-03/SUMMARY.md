# rl_only lower-role full-direction composed readiness on the ACTUAL
# champion checkpoint (drramp-acq1 s0) — the off-axis collapse never
# applied to it; it was always measured on an abandoned checkpoint
# (2026-10-03, idle-kick refill cycle, zero GPU spend)

## Why this item exists
Every piece of off-axis/full-direction forensics on record for the
`lower` role (`lowerrole_fulldir_headingsign_forensics_2026-10-03`,
`lowerrole_sectoraware_fix_2026-10-03`, `lowerrole_fulldir_n20_2026-10-03`)
was run against `..._s3_drramp_holdonly100_acq1.zip` — the
`goal.lower_hold_only_frac=1.0` checkpoint that was ADOPTED as champion
same-day, then REVERSED same-day (`lowerrole_holdonly100_evalcfg_
confound_2026-10-03`: an eval-cfg auto-replay confound, TRUE-protocol
score 0/36, it never practices the real descent). The STANDING champion
reverted to `..._s0_drramp_acq1.zip` (`drramp-acq1 s0`, 26/36=72%
forward, TRUE zero-`--lower-cfg` protocol) — but NO off-axis/full-
direction eval had ever been run against THIS checkpoint; every
`heading_deg`/`rot60` field on every `drramp-acq1-s0` report on disk
reads `0.0`/`False`. walkcurr/STATUS.md's "no cheap next lever
identified — needs a genuinely new structural idea" conclusion for the
composed off-axis gap was therefore resting on evidence from a
checkpoint that no longer exists as a candidate. This item runs the
missing eval before accepting that conclusion.

## Method
Reused the exact tooling built this week, zero code changes:
`eval_lifecycle_handoff_rlonly.py --stance currentcap29-s5-klrollback05-
acq15m --walk slew_smooth_s0 --rot60 --lower <s0-drramp-acq1> --lower-
recipe lowerrole_sac_drramp [--lower-rot60] --episodes 20 --heading-deg
<H> --seed 0`, zero `--lower-cfg` (matches the TRUE/protocol-clean
convention the confound fix established). All 8 `PINNED_HEADING_DEFAULTS`
headings x {baseline, `--lower-rot60` treatment} = 16 cells, launched in
parallel (128 cores free, CPU MuJoCo only), n=20/heading/arm, n=160/arm
total per variant. Reproducibility was explicitly checked this time
(the `lowerrole_sectoraware_fix_2026-10-03` item flagged an unexplained
non-reproducibility gap on a nearby panel): reran `h0`/baseline twice
more, back-to-back and against the original — all three runs' full
`summary` dicts are byte-identical. This panel is trustworthy.

## Finding: the champion ALREADY generalizes full-direction at ~72-76%,
matching its forward number — no off-axis collapse, no structural fix
needed

| heading | baseline direct | baseline plant | rot60-lower direct | rot60-lower plant |
|---|---|---|---|---|
| -135 | 14/20 (70%) | 17/20 (85%) | 15/20 (75%) | 13/20 (65%) |
| -90  | 17/20 (85%) | 14/20 (70%) | 16/20 (80%) | 16/20 (80%) |
| -45  | 15/20 (75%) | 10/20 (50%) | 16/20 (80%) | 17/20 (85%) |
| 0    | 15/20 (75%) | 13/20 (65%) | 15/20 (75%) | 13/20 (65%) |
| +45  | 10/20 (50%) | 19/20 (95%) | 16/20 (80%) | 12/20 (60%) |
| +90  | 15/20 (75%) | 16/20 (80%) | 11/20 (55%) | 18/20 (90%) |
| +135 | 15/20 (75%) | 16/20 (80%) | 15/20 (75%) | 16/20 (80%) |
| 180  | 14/20 (70%) | 16/20 (80%) | 15/20 (75%) | 17/20 (85%) |
| **TOTAL** | **115/160 (72%)** | **121/160 (76%)** | **119/160 (74%)** | **122/160 (76%)** |

Rise+walk composition is PERFECT at every heading/arm/variant (160/160
`gait_valid`, 160/160 `rise_valid_plant` where applicable, 0/320
`handoff_falls` across both variants) — the only variance is in the
`lower` attempt itself, consistent with the already-known 72% forward
number, not a new regression. Per-heading range (50-95%) is within the
~11pp binomial SE at n=20/cell around a true ~72-76% rate — this reads
as a FLAT distribution across all 8 headings, not a heading-sign split
or a forward-good/off-axis-bad shape. `--lower-rot60` TIES baseline at
this n (+4/160 direct, +1/160 plant, both well inside noise) — the
frame-alignment/sector-awareness question this week's tooling was built
to answer is answered: it does not matter for THIS checkpoint, because
there is no off-axis collapse for it to fix.

## What this does and does not change
**Reframes, not contradicts, every prior forensics doc this week**: the
heading-sign split, the rot60-lower INCONCLUSIVE panel, the 15%
"roughly uniform, unimpressive" `fulldir_n20` number were all real
reads of the `holdonly100-s3` checkpoint's actual behavior — that
checkpoint genuinely did collapse off-axis (and, per the confound root-
cause, was ALSO never a real forward standout to begin with: 0/36 TRUE-
protocol). None of that work was wasted; it correctly characterized the
checkpoint it was run on. It simply never transferred to ask the same
question of the checkpoint that actually remained champion after the
reversal.
**Does change** walkcurr/STATUS.md's open-gap framing: "composed full-
direction lifecycle readiness has no candidate above ~15-30% direct-arm
`lower_ok`" is WRONG for the standing champion — `drramp-acq1 s0` reads
~72-76% at EVERY heading, not just forward. The "no cheap next lever /
needs a genuinely new structural idea" conclusion was scoped to closing
a gap that does not exist on the actual champion lineage. No new
reward/curriculum/architecture lever is needed to clear full-direction
composed readiness at the SAME ~72-76% level the forward-only number
already implied.
**Does NOT change**: over_current remains the dominant lower-role
failure mode in absolute terms (its share of failures is unanalyzed
per-heading here, only the aggregate `lower_ok` rate) and 72-76% is
still well short of a clean PASS bar (the holdonly100 100%/92% numbers
that briefly looked like a real improvement are now known-FAIL/
confounded) — there is a genuine remaining quality gap, just not an
off-axis-SPECIFIC one. The terminal 2-leg (L2+L5) support habit and its
converged-stable-but-high-current nature (`lowerrole_terminal_support_
forensics_2026-10-02`) stand unchanged as the mechanism behind the
residual ~24-28% failures, now known to apply UNIFORMLY across heading
rather than being an off-axis-specific defect.

## Caveat this doc does NOT resolve: `s0` is a known lucky-seed draw
The same-day retrain-variance calibration (`s1-s4` zero-cfg-delta
reseeds landing 18/5/12/2 out of 36 forward-only, mean ~12.6/36 vs
`s0`'s 26/36) already established that `drramp-acq1 s0`'s 72% forward
number is a LUCKY SEED, not representative of the recipe family's
typical training outcome. This doc's ~72-76% full-direction number
inherits that exact same caveat — it shows `s0`'s luck is CONSISTENT
across heading (whatever made this seed's training run land well
generalizes to every direction, not just forward), which is itself
useful information (rules out "s0 just got lucky on the forward axis
specifically"), but it does NOT make the `drramp-acq1` recipe a
reliable from-scratch recipe, and does NOT mean a future reseed/retrain
would reproduce this off-axis number any more than it would reproduce
the forward one. Any composed-lifecycle claim built on this checkpoint
should keep citing it as "the s0 checkpoint", not "the drramp-acq1
recipe".

## Recommendation
1. `todaypolicy`'s `bundle_rlonly_lifecycle_v2` candidate should be
   re-scoped from "forward-heading-only, ~72% direct-arm" to "full-
   direction, ~72-76% direct-arm" — a materially stronger evidence
   package for the same zero-retrain checkpoint triple, changing the
   calculus on Next item 1(b)'s "operator acceptance of forward-
   heading-only... sufficient for a bounded Robot-Lab forward-only
   trial" framing (it no longer needs to be forward-only).
2. Do NOT chase a "genuinely new structural idea" for an off-axis-
   specific composed-lower collapse — it was never a property of the
   standing champion. The real remaining target (per terminal_support
   forensics, unchanged by this doc) is the universal ~24-28% residual
   failure rate at EVERY heading, dominated by the converged 2-leg
   terminal-support margin question — still unscoped, still needs a
   real idea, but it is a UNIFORM quality ceiling, not a directional
   one, which rules out any future lever framed around heading/sector/
   rotation-frame alignment specifically (this doc is decisive on that
   narrower question, unlike the earlier INCONCLUSIVE panel).
3. `rot60_lower.py`/`--lower-rot60` stays built+tested+available but is
   now confirmed NOT the fix for this checkpoint; do not invest further
   in sector-aware lower composition without a new, different
   checkpoint that actually shows a heading-dependent pattern first.

Evidence: `raw/{baseline,rot60lower}/h*.json` (committed, not /tmp —
learned from this week's own reproducibility-gap lesson), reproducibility
check against `/tmp/repeat_h0_check{1,2}.json` (byte-identical `summary`,
not committed, rerunnable in ~1 min from the command above).
