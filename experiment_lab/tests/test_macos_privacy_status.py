import subprocess

from hexapod_lab.macos_privacy_status import MacOSPrivacyStatus


def probe(monkeypatch, count, logs):
    calls = []
    responses = iter(["844\n", "p844\n" + "\n".join(f"f{i}" for i in range(count)), logs])
    monitor = MacOSPrivacyStatus()
    def run(arguments):
        calls.append(arguments)
        return next(responses)
    monkeypatch.setattr(monitor, "_run", run)
    return monitor._probe(), calls


def test_confirms_pressure_with_matching_privacy_error(monkeypatch):
    result, calls = probe(monkeypatch, 254, "SecStaticCodeCreateWithPath(file:///private/app) fails: 100024")
    assert result == {"state": "exhausted", "open_file_count": 254}
    assert "processID == 844" in calls[-1][calls[-1].index("--predicate") + 1]
    assert "private/app" not in str(result)
    assert calls[1][-1] == "-Fpf"


def test_high_count_alone_does_not_claim_exhaustion(monkeypatch):
    result, _ = probe(monkeypatch, 250, "")
    assert result["state"] == "unconfirmed"


def test_normal_count_skips_log_query(monkeypatch):
    result, calls = probe(monkeypatch, 8, "")
    assert result == {"state": "normal", "open_file_count": 8}
    assert len(calls) == 2


def test_probe_failure_remains_unknown_and_is_cached(monkeypatch):
    monitor = MacOSPrivacyStatus()
    def fail():
        raise subprocess.TimeoutExpired("lsof", 2)
    monkeypatch.setattr(monitor, "_probe", fail)
    monitor._refresh()
    assert monitor._status == {"state": "unknown"}
    assert monitor._next_check > 0
    assert monitor._running is False
