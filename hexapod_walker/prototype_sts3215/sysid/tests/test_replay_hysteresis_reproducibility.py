from sysid.replay_hysteresis_reproducibility import _compare


def test_compare_applies_numeric_tolerance_recursively() -> None:
    expected = {"x": [1.0, {"label": "ok"}], "flag": True}
    actual = {"x": [1.0 + 5e-10, {"label": "ok"}], "flag": True}

    assert _compare(expected, actual, tolerance=1e-9) == []
    mismatch = _compare(expected, {"x": [1.1, {"label": "bad"}]}, tolerance=1e-9)
    assert [row["path"] for row in mismatch] == ["$.flag", "$.x[0]", "$.x[1].label"]
