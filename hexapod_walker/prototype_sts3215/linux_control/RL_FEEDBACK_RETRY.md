# H1 RL feedback retry — 2026-09-14

The 50 Hz all-heading trial `rl_walk_20260914_205550` stopped after 2.1 policy seconds. Decoding its captured serial replies showed 10 incomplete snapshots among 116 combined write/read packets. Different servo IDs were missing (2, 3, 4, 6, 15); each missing reply recovered on the next packet. Policy inference averaged 0.308 ms. The direct one-off runner slept to the tick deadline before handling missing positions, then repeated the held command for another full tick. Recovered noise therefore produced 40–47 ms cycles and eventually three consecutive timing misses.

The direct one-off runner now attempts at most two read-only snapshots within the remaining original tick budget, requiring advancing sequence numbers and valid source ages. It neither sends another target nor feeds an incomplete pose into another policy inference. Three distinct fresh misses of the same coordinates still stop; insufficient budget retains the existing stale/hold path. Timing and freshness thresholds are unchanged.

A separate 25 Hz trial `rl_walk_20260914_205726` met its cadence (24.967 Hz, no late intervals) but requested raw knee joint 5 at 153 degrees, beyond its physical limit. The runner swallowed that ValueError and misleadingly called it stale feedback. Such errors now stop immediately, preserve support, and name the rejected command. Physical limits are unchanged. Do not retime a checkpoint or widen physical limits to get past either failure.

Mechanics checks: `uv run pytest rl_move/tests/test_rl_policy_timing.py -q` covers recovery within the original deadline, exhausted budgets, duplicate sequences, persistent missing coordinates, and rejected motor targets. These tests are not hardware gait validation.
