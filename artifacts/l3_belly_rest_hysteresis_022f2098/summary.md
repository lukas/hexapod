# L3 belly-rest radial shear hysteresis REPLICATE, 6 repeats — experiment `022f2098`

**The replicate completed on the first attempt: 1560/1560 ticks, all six cycles,
no trip, not one `/api/errors` row, robot left limp at logical zero. All six
cycles read exactly −0.703 deg = 8.0 encoder counts, sd 0.000 — reproducing
run 1's settled value exactly, with a between-run spread of 0.000 deg against
L1's demonstrated 0.230 deg.**

**And that precision changes the answer. L3 is NOT separable from the L5/L0
bracket. It is that bracket's lowest member.** Run 1 tentatively read L3 as an
intermediate third value; the replicate reverses that, and the reversal is the
substantive result.

## Result

Loop width = settled measured hip angle at the shared commanded −47.133 deg,
out-stroke minus in-stroke (settled = last 1.0 s of each 3.1 s dwell) — the
identical definition L0, L1, L2 and L5 used.

| cycle | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| run 2 loop (deg) | −0.703 | −0.703 | −0.703 | −0.703 | −0.703 | −0.703 |
| run 2 loop (counts) | 8.0 | 8.0 | 8.0 | 8.0 | 8.0 | 8.0 |

**Run 2 = −0.703 deg, sd 0.000, n = 6.** Run 1 was −0.6737, sd 0.0656, whose
entire sd was one 2-count event on cycle 1; its cycles 2–6 were also −0.703.

**Pooled two-run L3 = −0.6883 deg, sd 0.0508, n = 12 cycles / 2 runs
(−7.83 counts). Settled value −0.703 deg = exactly 8.0 counts.**

### The between-run spread is 0.000 deg, and it is not an average that happened to agree

All twelve settled windows in **both** runs hold a *single* value across all ten
of their 10 Hz samples. Both runs landed on the same two encoder counts:

- **out-stroke: −47.285 deg (count 538)** — all six cycles, both runs.
- **in-stroke: −46.582 deg (count 530)** — all six cycles of run 2, and cycles
  2–6 of run 1. Run 1's cycle 1 alone read count 532.

538 − 530 = 8 counts. This is the same discrete count twice, not two means that
coincided.

### Why L1's 0.230 deg is not a bound L3 has to inherit

The plan asks for the spread to be set against L1's demonstrated 0.230 deg.
L3's is **0.000** (settled) / **0.029** (6-cycle mean). Two facts stop 0.230
from being treated as a family-wide bound:

1. **L1's big between-run spread comes with a big within-run scatter.** Its
   per-run sds are 0.123, 0.149, 0.065 and its cycles bounce between 2 and 8
   counts *inside a single run*. L3 has none of that — run 2's within-run sd is
   exactly 0.000.
2. **L2 has more runs than L1 (4 vs 3) and a between-run spread of only
   0.072 deg.** So 0.230 is the family's outlier, not its norm.

**Honest limit:** n = 2 runs cannot prove L3's population spread is truly zero.
It shows the two runs landed on the same encoder count.

## Is L3 separable from the L5/L0 bracket? No.

| leg | loop (deg) | counts |
|---|---|---|
| L1 | −0.330 | 3.75 |
| L2 | −0.4357 | 4.96 |
| **L3 (two runs)** | **−0.703** | **8.00** |
| L5 | −0.832 | 9.47 |
| L0 | −0.967 | 11.00 |

Adjacent gaps, in counts: L1→L2 **1.20**, L2→L3 **3.04**, L3→L5 **1.47**,
L5→L0 **1.54**.

**L3 sits 1.47 counts from L5. L5 and L0 — the two legs already accepted as one
bracket — sit 1.54 counts apart.** L3's distance to the bracket is *smaller than
the bracket's own internal spacing*. Accepting {L5, L0} as one group forces
{L3, L5, L0} to be one group at the same standard. The real discontinuity in the
five-leg series is **L2→L3 at 3.04 counts**, more than double any other adjacent
gap.

Two questions are kept apart, because conflating them is how one number becomes
a wrong bracket:

- **Is L3's *value* distinguishable from L5's?** *Yes.* 1.47 counts against a
  measured between-run spread of 0.00–0.33 counts. A gait must not use one for
  the other.
- **Is L3 *separable from* the L5/L0 bracket as a cluster?** *No*, for the
  spacing reason above.

Run 1 could not decide this: its gap to L5 was 0.158 deg against an
assumed-applicable 0.230 deg spread, so "third value" and "belongs to the high
bracket and read low" were indistinguishable. The replicate resolves it.

## What this delivers for the gait

The open question that justified this run was whether L3's number could be used
as a **per-leg gait constant**. It now can: **L3 = 8.0 encoder counts
(−0.703 deg), reproduced exactly across two independent runs.** That is the
deliverable. L4 still has no number at all and is the natural next leg.

## The two plan questions

**1. Loaded-versus-unloaded offset per cycle?** Yes, all six. Out-stroke error
−0.152 deg and in-stroke +0.551 deg on **every** cycle — matching run 1's
cycles 2–6 exactly. Peak current on the moving joint **0.026 A** against a
0.75 A trip, the same 0.026 A run 1 measured. The loaded stroke draws roughly
4–8× the unloaded stroke (0.0088–0.0116 A vs 0.0012–0.0030 A) at loads of
4.0–5.1 % vs 3.2–3.9 %.

**2. Does hysteresis drift across repeats?** No. All six cycles identical; the
declared post-hoc monotonicity check reports no growth.

## Safety and supervision

| check | outcome |
|---|---|
| ticks | 1560/1560, worker done after 161.36 s, final state limp |
| new `/api/errors` rows | **0** — the single tolerated bus_timing allowance was not spent (run 1 spent it) |
| peak current | 0.026 A (trip 0.75 A, ceiling 3.0 A) |
| max temperature | 32 C (trip 55 C) |
| L3 knee rise | **0 C** (baseline 29 C, post 29 C; trip +8 C) |
| servo health | 18/18 pre and post, three advancing healthy samples each |
| non-L3 joint departure | worst joint 16 at 0.439 deg (trip 1.0 deg) |
| commanded foot clearance | 65.95 mm above the floor plane (requirement ≥ 15 mm) |
| tracking error | no trip (limit 30 deg) |
| cameras | 795 frames, 265 per camera, max gap 0.709 s against a 2.0 s watchdog |
| chassis tag watch | **MEASURED** — max shift 31.5 mm (trip 120), max yaw 4.86 deg (trip 15), 0 trips |
| command lease | held by `guarded-runner-022f2098` for the whole window, released cleanly |
| final pose | hip −0.18, knee −0.09 — the same 2-count residual run 1 left |

**Realtime vs post-hoc stop coverage** was declared and committed *before*
arming (`preflight_declaration.json`, commit `b214a4c5`): 12 of 17 conditions
enforced live in-loop, 5 post-hoc, each with its reason. Unchanged from run 1
because the runner is byte-identical.

**The tag watch is strictly better evidence than run 1's.** Run 1 could not
resolve a baseline and recorded UNMEASURED, which the plan expressly allows.
This run resolved a baseline from 5 samples and ran the watch live for the whole
window. Its err95 (32–195 mm) is larger than the 31.5 mm largest observed shift,
so it is reported as a *passed bound on gross motion*, not as a measurement of
real movement — exactly the scope the plan assigns it.

## Byte-exactness

- Protocol `l3_belly_rest_radial_shear_hysteresis_repeat6_v1`, canonical
  `protocol_hash` **c3727df8dc7e** — recomputed and matched.
- Runner **sha256 a66f0b5b37ef…, byte-identical to 7b565e2a's**. Everything that
  differs between the two runs (label, lease owner, output dir, protocol path)
  is already a runner environment variable, so the script needed no edit at all.
- Installed robot source md5-identical to this checkout across `sysid_runner`,
  `sysid_protocol`, `command_lease`, `mcu_feetech_bus` and `async_bus_guard`.
  **Nothing was deployed.**
- Only columns 10 and 11 vary in all 1560 rows; j9 constant at 0; the other 16
  joints exactly 0.0.

One documentation correction was made against run 1's declaration: it described
the executor's in-loop active-joint scope as "L3 hip j1 and knee j2". Those
indices are L0's, inherited from the runner this family descends from. L3's are
j10/j11. The executed scope was always the protocol's own varying joints.
