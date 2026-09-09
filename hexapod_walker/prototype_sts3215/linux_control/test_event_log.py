"""Event producers must remain independent of slow durable log sinks."""
from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
import queue
import threading

import pytest


@pytest.fixture
def log(monkeypatch, tmp_path):
    # Load isolated state without starting the module's automatic logger.
    # Its supported failed-configuration path exits before sockets/threads.
    unavailable_directory = tmp_path / "not-a-directory"
    unavailable_directory.write_text("")
    with monkeypatch.context() as isolated:
        isolated.setenv("HEXAPOD_LOG_DIR", str(unavailable_directory))
        spec = importlib.util.spec_from_file_location(
            "isolated_event_log", Path(__file__).with_name("event_log.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    module._configured = True
    module._fh = io.StringIO()
    module._err_fh = io.StringIO()
    yield module
    while not module._q.empty():
        module._q.get_nowait()
        module._q.task_done()


class Sink(io.StringIO):
    def __init__(self, block_operation=None):
        super().__init__()
        self.block_operation = block_operation
        self.entered = threading.Event()
        self.release = threading.Event()
        self.flushes = 0

    def _block(self, operation):
        if self.block_operation == operation:
            self.entered.set()
            if not self.release.wait(2):
                raise TimeoutError("test did not release the fake sink")

    def write(self, line):
        self._block("write")
        return super().write(line)

    def flush(self):
        self._block("flush")
        self.flushes += 1
        return super().flush()


@pytest.mark.parametrize("sink_name,operation", [
    ("_fh", "write"), ("_fh", "flush"),
    ("_err_fh", "write"), ("_err_fh", "flush"),
])
def test_emit_returns_while_durable_sink_is_blocked(log, sink_name, operation):
    sink = Sink(operation)
    setattr(log, sink_name, sink)
    writer = threading.Thread(
        target=log._write_line, args=("prior error", b"prior error\n", True))
    emitted = []
    producer = threading.Thread(target=lambda: emitted.append(
        log.emit("control", "next tick", level="error")))
    writer.start()
    try:
        assert sink.entered.wait(0.5), "writer never reached the fake sink"
        producer.start()
        producer.join(0.5)
        assert not producer.is_alive(), "emit waited for a filesystem operation"
        assert not sink.release.is_set()
        assert log.recent() == emitted
        assert json.loads(log._q.queue[0][0])["msg"] == "next tick"
    finally:
        sink.release.set()
        writer.join(0.5)
        if producer.ident is not None:
            producer.join(0.5)
    assert not writer.is_alive()


def test_writes_preserve_fifo_and_flush_error_sidecar(log):
    log._fh, log._err_fh = Sink(), Sink()
    first = log.emit("control", "first")
    second = log.emit("control", "second", level="error")
    while not log._q.empty():
        item = log._q.get_nowait()
        log._write_line(*item)
        log._q.task_done()
    assert [json.loads(line) for line in log._fh.getvalue().splitlines()] == [
        first, second]
    assert json.loads(log._err_fh.getvalue()) == second
    assert log._fh.flushes == log._err_fh.flushes == 1


def test_full_queue_drops_low_priority_and_retains_new_error(log):
    log._q = queue.Queue(maxsize=2)
    log.emit("control", "oldest")
    second = log.emit("control", "second")
    log.emit("control", "dropped")
    error = log.emit("control", "confirmed stop", level="error")
    assert log._dropped_events == 1
    assert [json.loads(item[0]) for item in log._q.queue] == [second, error]


def test_reconfigure_does_not_close_a_sink_during_a_write(log, monkeypatch, tmp_path):
    sink = Sink("write")
    log._fh = sink
    log._path = tmp_path / "previous.jsonl"
    monkeypatch.setattr(log, "_ensure_sock", lambda: None)
    monkeypatch.setattr(log, "_ensure_worker", lambda: None)
    monkeypatch.setattr(log, "_refresh_broadcast_targets", lambda port: None)
    log._beacon_thread = type("Alive", (), {"is_alive": lambda self: True})()
    destination = tmp_path / "next.jsonl"
    writer = threading.Thread(target=log._write_line, args=("prior", b"prior", False))
    configuring = threading.Thread(target=log.configure, kwargs={"path": destination})
    writer.start()
    try:
        assert sink.entered.wait(0.5)
        configuring.start()
        configuring.join(0.05)
        assert configuring.is_alive()
        assert not sink.closed
        assert log.emit("control", "during rotation")["msg"] == "during rotation"
    finally:
        sink.release.set()
        writer.join(0.5)
        if configuring.ident is not None:
            configuring.join(0.5)
    assert not writer.is_alive() and not configuring.is_alive()
    assert sink.closed
    assert log._path == destination
    log._fh.close()
