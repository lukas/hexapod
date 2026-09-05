import json

from rl_move.scripts.trace_stop_ordering import CASES, EVENT_FIELDS, run


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
    for case in ("sampler_thread_delay", "write_due", "skip_write"):
        stop = next(row for row in rows if row["case"] == case and row["event"] == "interlock_stop")
        assert stop["tick"] == 11
        assert not any(row["event"] == "bus_write" for row in rows if row["case"] == case)

    assertions = json.loads((first / "assertion_results.json").read_text())
    assert assertions["passed"] is True
    assert assertions["case_count"] == 5
    assert all(item["passed"] for item in assertions["assertions"])
