# cw-cpg-teacherfork-ab-cpgv1-b8m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-03T13:14:01+00:00

**pod**: hexapod-mjx-train-5

**steps**: 8000000

**parent**: cw-cpg-teacherfork-ab-cpgv1

**hypothesis**: Plain English: cpg/STATUS.md's own Next item 3 flags that ONE 2M-step data point (cw-cpg-teacherfork-ab-cpgv1, VERDICTED INFORMATIVE/WORSE-BUT-WALKING: the CPG-search motion library sustains real AMP-style walking but with det margins ~15-20% softer than the scripted teacher_v2, sto matched/better) is not enough to decide a teacher-library adoption fork -- explicitly 'not funded this cycle, amp M4 composition has GPU priority' on 08-23, now free (11 idle GPU slots, empty backlog, no cpg/amp GPU contention). Single lever vs cpgv1: --steps 2M->8M (matched-larger-budget, same BC-clone init/same reward/same amp-motion-lib=cpg_v1.npz/same seed 7), answering whether the softer-margin gap holds, closes, or widens once the discriminator+policy have a realistic training budget instead of a 2M discovery-scale snapshot.

**gate**: Read eval_amp_m5 (or the DR-0 gate + own-DR walk panel if m5 isn't wired for this lineage) det+sto walk margins (gait_valid, net fwd travel, slip/m) against BOTH style05's own numbers (the teacher_v2-library parity bar) AND cpgv1's own 2M numbers. PASS/CLOSES = margins now clear style05's bars at parity (within noise) -- promote cpg_v1 as a viable AMP style source, no adoption yet (still needs the cpg-clone-init cell before a real fork). PARTIAL = margin gap shrinks (>=30% closer to style05) but doesn't fully clear -- keep WORSE-BUT-WALKING verdict, note budget-dependence. FAIL/WIDENS = gap flat or worse than the 2M read, or any new fall/collapse -- closes the matched-larger-budget cell, leaving CPG-clone init as the only remaining lever before the adoption question is fully closed.

**refused_reason**: discovery runs cap at 2000000 steps (asked 8000000): the question is 'did qualitatively correct behavior emerge?' - continue as --phase hardening with --evidence.

