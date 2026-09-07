# Walking findings preserved September 7, 2026

These files preserve the completed RL campaign, the completed physical
alpha/speed comparison, and the later raw command-timing analysis. The
source manifest records the original locations and byte hashes. Raw physical
recordings and full experiment transcripts remain in Robot Lab's sealed
experiment store.

## Timing clarification after the physical report

The command stream targets 100 Hz (one update every 10 ms). The raw recorder
captures actual host writes; the approximately 48 Hz decoded `sync_write`
log is rate-limited and does not measure the motor-command rate.

Across the four eight-second physical trials, the raw capture contains
3,076 command intervals, including 15 longer than 20 ms (about 0.49%).
The longest is 28.242815 ms. The mean rate of approximately 97–98 Hz and
absence of captured exchange failures do not establish consistent deadlines.
Feedback or snapshot requests occur between the writes in nine of the 15
long gaps, including the worst. Source inspection found those reads and
motor writes use the same transaction lock in `mcu_feetech_bus.py`.
Polling can therefore delay a command. Other gaps have no intervening read;
this is not a complete causal attribution of every delay.

Timestamps are recorded after the host serial write, before the later flush
and reply handling. They are not per-servo application timestamps. The
capture reports no communication drops, uncaptured bytes or write errors.

Keep the 100 Hz target. Reducing contention from telemetry polling is a
concrete next timing intervention; these data do not show that 100 Hz is
infeasible, justify retraining at 50 Hz, or establish timing as the cause of
visible shaking. No timing fix or new physical test was performed for this
analysis. The acceleration comparison in the earlier physical report is
also a proposed experiment, not a completed result.
