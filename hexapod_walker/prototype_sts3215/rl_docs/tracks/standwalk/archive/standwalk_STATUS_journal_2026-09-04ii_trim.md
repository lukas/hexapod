# standwalk STATUS journal archive 2026-09-04ii (verbatim)

Update, 2026-09-04 ~15:3x (this cycle): closed the `cont-s1b` falsifier
(training finished clean, W&B state=finished @2.03M steps) — ran
`probe_turn_authority` on the pod (train-9), full 84-key non-`train.*`
cfg-set replayed from its own ledger `extra_args`. Then re-ran it
through `rescore_turn_authority.rescore_cell` (the SAME both-signs
tool that produced the 5/10 seed1 flip) against both `cont` and
`cont-s1` as controls, not just the shorthand positive-only numbers
quoted in the falsifier's gate text. **Result is neither branch the
falsifier pre-registered — a third, SIGN-ASYMMETRIC pattern:**
pure-turn/combined vs `cont` = +14.1%/+0.7% (positive dir, "strong,
matches cont") but -15.1%/-36.9% (negative dir, "weak, WORSE than
cont-s1"); vs `cont-s1` = +28.5%/+26.6% (positive) but -10.8%/-2.6%
(negative). Raw wz_med: pos pure-turn 0.196 (beats `cont`'s 0.172),
neg pure-turn -0.170 (below even `cont-s1`'s -0.190). The shorthand
positive-only read ("0.196/0.132, lands at/above `cont`'s 0.172/0.132,
FAIL wall re-closes") would have been a false-clean answer — the
negative-command floor independently reproduces-or-worsens the
`cont-s1` weak read. **This means a single matched-continuation
control (n=1 per seed) is not a stable comparator** for this axis:
three independent seed1-family continuations (`cont-s1`, `cont-s1b`,
and by extension every lever-arm's own continuation) now show
run-to-run turn-authority variance large enough, and asymmetric
enough between +/- command, to plausibly explain the whole 5/10 flip
as control noise rather than a real per-seed dynamics effect — but it
could equally mean genuine per-run bimodality. Left `cont-s1b`
UNVERDICTED (mechanism-health canary, no fixed pass/fail; the decisive
question is the fork, not this run's own pass/fail). Evidence:
`logs/ckpt_eval/probe_turn_authority_cap29_stdwalklohi_cont_s1b_
combined_09-04.json`. **DIG-IN owed** (flagged this cycle) — do not
spend on the 5 reopened lever cells nor re-close the FAIL wall until
a deep-model pass decides: (a) treat +/- signs as two independently-
scored sub-questions instead of collapsing to one number, or (b) some
other resolution. Started building resolution path (a)'s prerequisite
same cycle: launched `cont-s1c` (seed=31, train-9) and `cont-s1d`
(seed=41, train-1), both VERIFIED RUNNING, 2M steps, exact same
recipe as `cont-s1`/`cont-s1b` (init-from the frozen `cap29-stdwalklo-
hi-s1` checkpoint, zero lever, only trainer seed differs) — by next
read there will be n=4 independent seed1-family continuations to
compute a real per-sign spread instead of trusting any single draw.
