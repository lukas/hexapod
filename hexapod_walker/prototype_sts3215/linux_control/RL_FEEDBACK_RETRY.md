# H1 RL feedback retry — 2026-09-14

The 50 Hz all-heading trial `rl_walk_20260914_205550` stopped after 2.1 policy seconds. Decoding its captured serial replies showed 10 incomplete snapshots among 116 combined write/read packets. Different servo IDs were missing (2, 3, 4, 6, 15); each missing reply recovered on the next packet. Policy inference averaged 0.308 ms. The direct one-off runner slept to the tick deadline before handling missing positions, then repeated the held command for another full tick. Recovered noise therefore produced 40–47 ms cycles and eventually three consecutive timing misses.

The direct one-off runner now attempts at most two read-only snapshots within the remaining original tick budget, requiring advancing sequence numbers and valid source ages. It neither sends another target nor feeds an incomplete pose into another policy inference. Three distinct fresh misses of the same coordinates still stop; insufficient budget retains the existing stale/hold path. Timing and freshness thresholds are unchanged.

A separate 25 Hz trial `rl_walk_20260914_205726` met its cadence (24.967 Hz, no late intervals) but requested raw knee joint 5 at 153 degrees, beyond its physical limit. The runner swallowed that ValueError and misleadingly called it stale feedback. Such errors now stop immediately, preserve support, and name the rejected command. Physical limits are unchanged. Do not retime a checkpoint or widen physical limits to get past either failure.

Mechanics checks: `uv run pytest rl_move/tests/test_rl_policy_timing.py -q` covers recovery within the original deadline, exhausted budgets, duplicate sequences, persistent missing coordinates, and rejected motor targets. These tests are not hardware gait validation.

## Hardware follow-up

Deployed source commit `564d602f2` to H1; the remote runner SHA-256 matched `7767cd82547dcb68f601363007a352d91837e5269bf4b67228f8404c2647ae0a`. Two three-second trials of `walk_allheading_mlp_singleframe_scratch_50hz.json` completed all 150 ticks without timing/freshness stops: backward command at 21:05 UTC measured 49.703 Hz (7 recovered samples, maximum period 26.743 ms); lateral command at 21:07 UTC measured 49.869 Hz (3 recovered samples, maximum period 24.926 ms). Isolated late intervals remain; no deadline limits were relaxed.

Both trials remained in camera coverage without observed collisions. They produced leg cycling/body shift and appreciable final lean; neither proves sustained walking or reliable commanded direction. H1 was returned to an observed belly-down, legs-out pose using the existing direct stance ease and then disarmed. The default Safe Zero/STEP-down entry still refuses stale unreachable keyframes, and direct stance completion can still report an isolated missing coordinate. These separate issues were not fixed by the RL stream retry change. Full records and two-camera clips are in `artifacts/h1-rl-angle-fixed-20260914` in the user's primary workspace.
