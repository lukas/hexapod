# L0 belly-rest radial shear hysteresis, 6 repeats — experiment `881677a0`

**The run completed: 1560/1560 ticks, all six measured cycles, no trip, robot
left limp at logical zero. L0's loop width is −0.967 deg, and every one of the
six cycles returned that same value exactly — sd 0.000.** That is the largest
per-leg loop this family has measured and the only one with no cycle-to-cycle
scatter at all.

Getting there took a deployment repair and a focused executor fix; both are
recorded below, because two 156 s runs were refused before any motion and the
reason was ours, not the robot's.

## Result

Loop width = settled measured hip angle at the shared commanded −47.133 deg,
out-stroke minus in-stroke (settled = last 1.0 s of each 3.1 s dwell) — the
identical definition L1, L2 and L5 used, so the numbers are directly
comparable.

| cycle | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| loop (deg) | −0.967 | −0.967 | −0.967 | −0.967 | −0.967 | −0.967 |

**L0 = −0.967 deg, sd 0.000, n = 6 cycles / 1 run**, i.e. exactly 11.0 encoder
counts at 0.0879 deg/count.

### The zero variance is real, and it is quantization

This was checked rather than reported. In all **12** settled windows the ten
10 Hz samples are *byte-identical to each other*: −47.373 deg at every
out-stroke dwell and −46.406 deg at every in-stroke dwell, with no other value
appearing anywhere. Those two readings are exactly 11 counts apart and sit on
the same count grid. The encoder does not move at all during the settled
second, and it lands on the same pair of counts on every repeat.

So sd 0.000 is not a suspiciously clean statistic — it is the honest statement
that this measurement has **no resolvable within-run variation**: the loop is
11 counts wide and the instrument cannot see anything finer.

### Where L0 sits against the other legs

| leg | loop (deg) | sd | n cycles / runs |
|---|---|---|---|
| **L0 (this run)** | **−0.967** | **0.000** | **6 / 1** |
| L1 | −0.330 | 0.153 | 18 / 3 |
| L2 (plan's `compare_against`) | −0.4357 | 0.077 | 24 |
| L5 (plan's `compare_against`) | −0.832 | 0.065 | 25 |

L0 is the stiffest-hysteresis leg measured: 2.9x L1, 2.2x L2, and 1.16x L5.
Notably −0.967 is exactly L5's own *worst* recorded cycle, so L0 and L5 are
adjacent members of a high band while L1 and L2 sit together near −0.33/−0.44.
That is a **four-leg, two-bracket** picture, consistent with what the L1 run
concluded, with L0 joining L5 at the high end rather than opening a third
bracket.

### The one thing this run cannot tell you

**A single run's sd is not the uncertainty on L0's loop width.** The L1
experiment established this directly and it is the most important caveat here:
three replicate runs of a byte-identical protocol on the same leg, same rig,
same hour gave run means spanning 0.230 deg, and its between-run sd (0.097)
was as large as its mean within-run sd (0.118). L0's sd of 0.000 measures
within-run repeatability only. It is *evidence that the leg is quiet*, not
evidence that a second L0 run would land on −0.967. The saved plan asked for
six cycles with drift checked across repeats, and that is delivered; a
replicate run is the natural next step, and is the single measurement that
would most improve this number.

## The two plan questions, answered

**1. Is the loaded-versus-unloaded offset quantified per cycle?** Yes, all six,
with the loaded (in-stroke) error +0.727 deg and unloaded (out-stroke) error
−0.240 deg against the slewed command, identical on every repeat.

**2. Does hysteresis drift across repeats?** No. The declared post-hoc
monotonicity check finds all six loops equal, so there is no growth of any
kind, let alone monotonic growth beyond the reviewed bound. Peak current on the
moving joint stayed at 0.039 A against a 0.75 A trip, and the L0 knee rose 1 C
against an 8 C bound, so nothing was heating or binding across the repeats
either.

## Safety and observation record

- **Chassis never stood and never moved.** IMU roll moved 0.18 deg and pitch
  0.14 deg across the whole window against a 10 deg trip. The worst *measured*
  non-L0 joint stayed **0.439 deg** from logical zero across all 1560 ticks,
  against the plan's 1.0 deg bound. Pose before and after the run is identical:
  worst joint 0.44 deg.
- **Chassis-tag-versus-floor-tags watch: ENABLED and clean.** The plan makes
  this conditional on the arena lighting being restored; it has been (mean luma
  49.8/23.0/24.4 against the L1 run's 24.9/4.6/4.4, and the tracker resolves
  10–14 tags per view where it reported "tags: none" on all three views at
  05:06Z). 142 samples, 45 resolved, median radial offset **6.18 mm**, max
  85.18 mm, median yaw delta 0.98 deg; the 120 mm / 15 deg bound was never
  approached on three consecutive resolved samples. For scale, the same tag
  measured over 40 s with the robot untouched wanders up to 39.7 mm on its own.
  *Honest limit:* this bounds gross motion only — the tag's own error_95 is
  ~93 mm. Fine stillness rests on the joint telemetry above.
- **Cameras:** all three recorded continuously from the `:8766` camera server
  for the whole window — 267 frames each over 174.7 s (run window 161.0 s),
  zero capture errors, every frame sha256 distinct, **max inter-frame gap
  0.714 s** against the 2 s staleness abort bound.
- **Thermal / electrical:** peak current 0.039 A on any joint (per-servo trip
  0.75 A, hard ceiling 3.0 A); max logged temperature 35 C (trip 55 C); L0 knee
  32 C → 33 C, a **1 C rise** against the +8 C bound.
- **Exclusive command lease** held by `guarded-runner-881677a0` for the whole
  window and released cleanly. Its exclusivity was demonstrated for this run
  rather than cited: direct and `:8898` hub `/api/rl/stand|lower|walk`, plus
  `/api/standup` and `/api/sysid/run`, all refused 409, while `/api/rl/stop`,
  `/api/standup/stop` and `/api/safe_zero` all still answered 200 with the
  lease held. No foreign command was observed during the window.
- **Three advancing healthy 18/18 samples** before arming, L0 knee baseline
  32 C, start pose worst joint 0.44 deg against the plan's **1.0 deg** gate.

## The one `/api/errors` row, tolerated exactly as the plan allows

At **14:54:29.362Z**, mid-run, the recurring host-MCU bare-ERR row appeared:
`P->p ascii_err 16.0ms`, `src: mcu`, `n=0`, `pre_a5_ascii "ERR"`. The reviewed
classifier (`mcu_feetech_bus.classify_bare_err_reply`, commit c1f8067c) put it
on the **`desync_guard`** reject path — an attributed torn frame, not a cable
fault. Self-recovery was then *confirmed*, not assumed: the on-robot CSV grew
from 486,004 to 490,024 bytes within the window and the bus stayed available
and unquarantined. The run continued and completed.

This is the plan's own wording — "any new `/api/errors` row **beyond a single
self-recovered transient bus_timing retry**" — enforced literally, and it is
the difference between a result and no result. The L1 sibling's runner halted
on the first row of any kind, which is stricter than its plan asked, and that
cost it the closing glide of run 2 at tick ~1430 of 1560. Here the allowance
was spent once, on exactly the row class it was written for, and a second row
or any row of another kind would have halted immediately.

## Why the first three attempts did not produce data

Recorded in full because two of them were our own defect, and one physical
attempt did start motion.

| attempt | outcome | motion |
|---|---|---|
| run1 14:40:13Z | refused: `runtime state stream incomplete: joints [2]` | none |
| run2 14:42:21Z | refused: `telemetry admission failed: sample 1 incomplete: 17/18 servos` | none |
| run3 14:49:49Z | halted at tick 0 by `bus_timing` `ack_rejected` (`W->OK`, n=18) | started, ~2 s |
| **run4 14:52Z** | **completed 1560/1560** | full protocol |

**Attempts 1 and 2 were a defect in the executor, not a fault in the robot.**
Both pre-motion gates were single-shot: one dropped servo reply refused a whole
156 s run. Three fresh 18/18 samples taken seconds either side of each refusal
were clean and joint 2 read 0.18 deg / 32 C / 0.0 A throughout. That is
inconsistent with every other missing-reply rule in the system — the command
loop already required three consecutive misses, `_read_pose_debounced` already
merged retries for the pre-glide pose read "so one dropped ID never trips", and
this plan itself carries `missing_servo_consecutive_reads: 3`. The debounce
existed and had simply not been applied to these two reads. Fixed in
`71459673`, deployed, and pinned by tests in both directions.

**Attempt 3 was correctly refused.** Its row was `ack_rejected` on a framed
18-servo `W` transaction, which commit 89547745 explicitly says must *not*
inherit the bare-ERR torn-frame attribution. The tolerance is narrow by
construction and rejected it on the `n=0` signature. Robot was clean
afterwards — 18/18, 32 C, 0 A, L0 back at logical zero, one error row — so this
was a transport fault, not a mechanical hazard, and the retry after camera plus
three fresh healthy samples was the sanctioned response.

## The lease had to be restored first

`execution.exclusive_command_lease_required: true` is a hard requirement of
this plan, and `/api/command-lease` returned **404** at preflight. A clean
deploy of `main`@`d54d81e4` at **13:55:49Z** — eight minutes before this job
started — had removed it; the lease lives only on the lab's engineering branch.
This is the second time it has happened, and `deploy_when_lab_idle.sh` in main
documents the first ("the same deploy silently reverted the guard fix the lab
had just shipped from its own branch").

The repair honours the overwrite fence rather than redeploying our own branch,
which would have rolled back 38 commits of main's work: an integration branch
was built **on the installed revision** (`robot-deploy/l0-lease-on-d54d81e4`),
adding only the four lease and bare-ERR commits. Zero commits are lost relative
to what was installed, and main's own guards were verified still present on the
robot afterwards (`safe_zero` `GUARD_CONFIRM_READS` 9, `standup`
`IMPLAUSIBLE_FAULT_READS` 2).

**These commits are still not on `main`, so the next clean-main deploy will
drop the lease again.** Merging them is the durable fix.

## Protocol identity and admission

The reviewed document was submitted **byte-exact and unmodified** to
`POST /api/sysid/run` (`sysid_protocol` v1), no parameter edits. Canonical
`protocol_hash` **`8709926b4c01`**; file sha256
`a91586507b380dde2a2e34ab80559b4485fbd8406253dcd881cab831ed5b3e6c`. The plan
derives it from `a99ceef28136` (L2) by remapping only the two varying hip/knee
columns; the generator only accepts an `l5_`-named source, so the review proves
the claim directly instead — L0's `j1`/`j2` columns are byte-identical to L2's
`j7`/`j8`, `t_s` matches, and every non-trajectory field compares equal to L2's.

Realtime-versus-post-hoc stop coverage was declared **before arming**
(`preflight_declaration.json`, committed in `37b19d22`): 12 realtime, 5
post-hoc, with the reason each post-hoc item cannot be enforced live without
adding the bus load it exists to detect. All five post-hoc checks were run and
all pass.

## Evidence

`sysid_..._20260910_145225.csv` is the run's own 10 Hz synchronized telemetry
(all 18 measured angles, all 18 currents, load, temperature).
`l0_run4_loop_metrics.json` recomputes the six per-cycle loop widths from it and
`l0_run4_posthoc.json` recomputes every declared post-hoc check, including the
12 settled windows behind the zero-variance finding.
`analyze_l0_hysteresis.py` and `posthoc_checks_l0.py` are sealed alongside, so
every number above is reproducible from the artifacts.
`camera_and_tag_coverage.json` carries the per-camera frame accounting and the
chassis-tag analysis; `run4/frame_index.jsonl` carries every frame's sha256.
