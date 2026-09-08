# Leg-duty ratio reward activation repair

The four 2M canaries from cycle `20260907T234849` did not activate
their intended new reward. Their checkpoints/evaluations are preserved,
but cannot establish whether the ratio reward helps.

`walk_task.py` put ratio EMA/counter updates inside an existing contact
bookkeeping condition that listed other contact rewards, but omitted
`g_ratio > 0`. Every listed alternative was disabled in the actual sparse
launch configuration. The counter therefore stayed zero and never reached
the three-second charge grace period. Existing tests enabled unrelated
step/drag/park rewards, accidentally opening the condition.

Confirmed directly on train0/1/2 at 2026-09-08 00:25 UTC. All had the same
affected walk_task.py SHA256:
`edfbecbd6d071ab8ca0e720fa85a2748ac17049ce1f6d4496edfc73b4c7793be`.
This was not a W&B field filter: MJX host workers use the shared post-step
logic, pass complete info dictionaries and log arbitrary numeric scalars.

Fix: `ebad6d0df28887877dabced80be306764f5a0e15`, pushed to main.
The new sparse-configuration gait and raised-leg regressions both failed
before the fix with counter zero. After the one-line condition fix,
**9 focused tests passed**. They verify counter advancement, grace timing,
post-grace scalar telemetry, negative starvation charge, total return
accounting and exactly unchanged honest-gait return. This is an activation
regression using controlled actors, not a full DR training replay.

Each affected ledger entry now has `watchdog_mechanism_validation` set to
`INVALID_MECHANISM_NOT_ACTIVATED`, with source evidence and feedback
`fb_20260908T002542_230a49`. No trainer was killed: all four had already
completed optimization when the omission was confirmed.

Recovery first replays s0-widen8-acq1-legdutyratiofresh as `-guardfix1`
for 2M steps, keeping its original s0-acq1 init checkpoint and RNG seed 2.
The new run does not initialize from the undosed attempt's output.
Its launch source `387ccac2cfd1fcc2bbf4d579ac19dcca762844d0` contains the
fix, and the corrected predicate was verified on train2. Runtime activation
is now confirmed: W&B `iwhaciad`, step 2,097,152, shortfall
0.15201348811093307 and charge -22.802023216640073, equal to
`-150 * shortfall` within 1.2e-13. Logged training FPS was 11,575.
The cloud owner independently confirmed activation and completed the other
three planned `-guardfix1` replacements. All retain original initialization
and RNG seeds (2/3/2/2); their held-out reports are pending at 00:49 UTC.
All four GPU trainers exited, leaving separate CPU artifact work.

Cloud focused validation passed 16 tests. The larger walk suite reported
164 passed, 24 failed and 4 skipped. Three failures were spot-reproduced
on the clean parent; that spot-check does not independently establish
the provenance of all 24 failures. The full suite was not green.
The original four ledger attempts retain their invalid-mechanism marker
and now have the owner's CANARY FAIL - INFRASTRUCTURE verdicts.

Keep the canary interpretation narrow: a short null does not close all
reward designs or establish a physical floor. The original synthetic bank's
reported undosed honest/flag-leg returns were already correctly ordered;
the new penalty increases separation in that example, rather than proving
an ordering reversal. Relevant feedback: `fb_20260908T002128_23e9e1`.
