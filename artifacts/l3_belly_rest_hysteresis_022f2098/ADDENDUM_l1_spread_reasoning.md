# Addendum — sharpening one argument in the sealed summary

The evidence for experiment `022f2098` is sealed (manifest `ca7051def2e8…`) and
is not edited by this note. Nothing in the result, the numbers, or the
conclusion changes. This records a **refinement of one supporting argument**,
made after the seal.

## What the sealed summary says

Under "Why L1's 0.230 deg is not a bound L3 has to inherit", reason 1 reads:

> L1's big between-run spread comes with a big within-run scatter. Its per-run
> sds are 0.123, 0.149, 0.065 and its cycles bounce between 2 and 8 counts
> *inside a single run*. L3 has none of that.

Every number there is correct. But "comes with" invites a causal reading — that
L1's between-run spread is *explained by* its cycle noise averaging out
differently each run. **That reading would be wrong, and it is worth stating
precisely.**

## The arithmetic

L1's three runs have per-run sample sds 0.1344, 0.1634 and 0.0712 deg, so the
standard error of a six-cycle run mean averages **0.050 deg**. The observed
between-run spread is **0.2299 deg — about 4.6× that standard error.**

Cycle-to-cycle noise alone does not produce a 4.6-sigma spread between run
means. **L1 has a genuine run-to-run offset**, a real physical instability from
one run to the next, on top of its large within-run scatter.

## Why the conclusion is unchanged — in fact better supported

This *strengthens* the case for not transferring L1's 0.230 deg onto L3. L1 is
not simply a noisier measurement of the same well-behaved quantity; it has a
run-to-run instability that L3 demonstrably does not exhibit. Importing L1's
number as a family-wide bound would be importing another leg's distinct
physical behaviour.

The two arguments that carry the real weight are, in order:

1. **Both L3 runs landed on the same two encoder counts** — out-stroke count
   538, in-stroke count 530, with every one of the twelve settled windows
   holding a single value across all ten of its samples. This is the same
   discrete count twice, not two means that happened to agree.
2. **L2, with more runs than L1 (4 vs 3), shows a between-run spread of only
   0.072 deg.** So 0.230 is the family's outlier, not its norm.

The within-run-scatter observation is a third, weaker point and should be read
as a description of how L1 differs from L3, not as an explanation of L1's
spread.

**The honest limit is unchanged and still governs: n = 2 runs cannot prove L3's
population spread is truly zero.** And the separability conclusion — that L3 is
not separable from the L5/L0 bracket, because its 1.47-count distance to L5 is
smaller than the 1.54 counts separating L5 from L0 — rests on the spacing
comparison alone and does not depend on this argument at all.
