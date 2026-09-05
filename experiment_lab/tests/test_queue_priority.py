from hexapod_lab.db import Store


def test_explicit_next_plan_preserves_older_work_and_fifo_ties(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")

    def add(name, priority=None):
        return store.create({
            "name": name,
            "duration_seconds": 1,
            "execution_mode": "external_guarded",
            "parameters": {} if priority is None else {"queue_priority": priority},
        }, "operator")

    older = add("L5 measurement")
    add("Metric repeat")
    malformed = add("String priority is not a priority", "999")
    first = add("Repair timing first", 10)
    second = add("Later urgent plan", 10)
    assert store.next_external_experiment()["id"] == first["id"]
    store.finish(first["id"], "succeeded")
    assert store.next_external_experiment()["id"] == second["id"]
    store.finish(second["id"], "succeeded")
    assert store.next_external_experiment()["id"] == older["id"]
    assert store.get(older["id"])["status"] == "waiting_for_operator"
    assert store.get(malformed["id"])["status"] == "waiting_for_operator"
