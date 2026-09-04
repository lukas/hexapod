# standwalk STATUS journal archive 2026-09-04jj (verbatim)

Update, 2026-09-04 ~16:2x (DIG-IN RESOLVED, deep-model cycle): the
5/10 seed1 lever-cell reopening was **COMPARATOR NOISE**; the
sign-collapsed single-control `rescore_cell` PASS is INVALID on this
axis. Completed the n=4 spread: `cont-s1c`/`cont-s1d` finished
training (final checkpoints on pod), ran both probes on their own
pods (full 84-key cfg replay from each run's own ledger) ->
`logs/ckpt_eval/probe_turn_authority_cap29_stdwalklohi_cont_s1{c,d}_
combined_09-04.json`. Evidence, three independent lines: (1)
control-vs-control cells trigger the old criterion — `cont` vs
`cont-s1` scores +25.8%/+54.2% combined and PASSes; (2) all 5
reopened cells flip to FAIL when the denominator swaps `cont-s1` ->
`cont-s1b`; per-cell PASS counts across the 4 control draws are only
0/4–2/4; (3) measured n=4 zero-lever seed1-continuation spread is
enormous on the positive clauses — pt_pos 0.119–0.196 (50% rel),
cb_pos 0.064–0.136 (65% rel; `cont-s1d` is the worst positive draw
yet, not an OOD-cfg artifact — its pt_neg 0.195 tracks fine) — vs
tight negative clauses pt_neg 0.170–0.198, cb_neg 0.120–0.138.
**Adopted methodology (encoded as `rescore_turn_authority band`,
tests green):** score the FOUR clauses (pure/combined x +/-)
separately against the control-DISTRIBUTION band (n>=3 matched
zero-lever continuations); WIN only above band max, LOSS only below
band min, in-band = no-call; family claims need clause replication
across lever draws. **Real per-sign finding the collapsed score
hid:** cb_neg collapses in 4/4 zero-lever continuations (0.127
+/-0.008) vs frozen parent-s1 0.142 and seed0 `cont` 0.190, while
9/10 lever arms sit ABOVE the band (0.14–0.19; binomial p~4e-6) —
geometry levers do NOT improve steering (cb_pos: 0/10 wins), they
partially PROTECT it against continuation erosion. Frozen parents
hold the best pure-turn by far (0.223–0.226 vs ALL continuations
0.119–0.214): plain 2M continuation of this lineage is actively
steering-destructive; any future continuation needs the 4-clause
probe as a canary vs the band. FAIL wall on "levers improve combined
turn authority" stays CLOSED; NO acquisition run on the 5 cells.
`cont-s1b` verdicted PASS (canary); `cont-s1c`/`cont-s1d` verdicted
on W&B-finish this same cycle. Launched `cont-b`/`cont-c` (seed0
zero-lever continuations, seeds 21/31) so the seed0 half of the wall
(currently scored 9/10 FAIL vs the single `cont` draw) gets the same
n=3 band treatment — also tests whether cb_neg-protection replicates
where the control (0.190) did NOT collapse. n=4 manifest:
`logs/ckpt_eval/rescore_turn_authority_09-04/manifest_n4.json`.

Prior updates (09-04 ~13:2x, ~14:1x, ~14:4x — mlcontprice2 FAIL-
MECHANISM/dose-bracket-to-k16 read, cont-s1b launch) archived verbatim
in `archive/standwalk_STATUS_journal_2026-09-04hh_trim.md`. `mlcontprice16`
(k=16.0 dose-bracket canary) is still VERIFIED RUNNING train-5, owned
by a concurrent cycle — see Next item 1.
