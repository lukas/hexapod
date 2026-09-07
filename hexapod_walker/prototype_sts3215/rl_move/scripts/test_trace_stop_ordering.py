import json

from rl_move.scripts.trace_stop_ordering import (
    CASES,
    EVENT_FIELDS,
    TICK_PERIOD_NS,
    run,
)


def test_trace_replay_is_deterministic_and_complete(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"

    first_result = run(first)
    second_result = run(second)

    assert first_result["passed"] is True
    assert first_result == second_result
    for name in ("event_trace.jsonl", "assertion_results.json", "input_hashes.json"):
        assert (first / name).read_bytes() == (second / name).read_bytes()

    rows = [json.loads(line) for line in (first / "event_trace.jsonl").read_text().splitlines()]
    assert {row["case"] for row in rows} == set(CASES)
    assert all(set(EVENT_FIELDS) <= set(row) for row in rows)
    assert [row["event_sequence"] for row in rows] == list(range(1, len(rows) + 1))
    for case in ("sampler_thread_delay", "write_due", "skip_write"):
        ticks = [
            row for row in rows
            if row["case"] == case and row["event"] == "snapshot_checked"
        ]
        stop = next(row for row in rows if row["case"] == case and row["event"] == "interlock_stop")
        assert stop["tick"] == 11
        assert not any(row["event"] == "bus_write" for row in rows if row["case"] == case)
        assert all(
            later["monotonic_time_ns"] - earlier["monotonic_time_ns"]
            == TICK_PERIOD_NS
            for earlier, later in zip(ticks, ticks[1:])
        )
        assert all(
            later["snapshot_age_ms"] - earlier["snapshot_age_ms"] == 10.0
            for earlier, later in zip(ticks, ticks[1:])
        )

    assertions = json.loads((first / "assertion_results.json").read_text())
    assert assertions["passed"] is True
    assert assertions["case_count"] == 5
    assert assertions["tick_period_ns"] == TICK_PERIOD_NS
    assert all(item["passed"] for item in assertions["assertions"])
