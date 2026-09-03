Update, 2026-09-03 ~05:0x (idle-kick, item 0 STILL mid-flight on
train-6/7, pace unchanged): closed the last open semantics-bank item,
`test_getup_honest_ordering` (genuine reward-design gap, not papered
over). Root cause: the same-day q0-frame fix made "freeze"'s held
pose correct (ret -40.4 buggy -> -30.3 accurate, cheaper to hold),
eating the 08-22 margin over "partial" (-35.1, untouched) since that
margin was only ever sized against freeze's old buggier cost. Fix:
`getup_k_progress` 200->350 (partial's ratchet income scales
~0.18/unit-k, freeze's ~flat 0.006) restores partial -8.2 > freeze
-29.3 (~20+ margin); swept 250->350, every other GETUP ordering stays
intact/widens. `-k getup`: 9/9 pass. Global default, but `p_getup`
isn't wired into any training recipe (0 ledger matches) so this is
SPECIFICATION work, no behavior change to anything running today.
Snapshotted+pushed (`exp/getup-honest-ordering-krecal-fix-0903`).
Closes the semantics-bank dig-in queue from the 09-02/09-03 window --
only RETIRED-track `walkcurr_pf` reds (~16-18) and whatever
`/tmp/full_after_tanglefix_0903.log` surfaces fresh remain. Full
derivation: OPERATOR_QUESTIONS.md.
