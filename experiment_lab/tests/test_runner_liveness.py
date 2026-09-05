import os
from pathlib import Path
import json
import signal
import subprocess
import sys
import threading
import time

from fastapi.testclient import TestClient

from hexapod_lab.config import Settings
from hexapod_lab.db import Store
from hexapod_lab.main import create_app
from hexapod_lab.runner import ExperimentRunner


def configured(tmp_path, **overrides):
    values = dict(
        data_dir=tmp_path,
        api_keys="admin:alice:secret",
        driver="simulated",
        robot_command=(),
        camera_input="",
        bind="127.0.0.1",
        port=8767,
        public_base_url="",
        auto_worker=False,
        max_duration_seconds=30,
    )
    values.update(overrides)
    return Settings(**values)


def process_is_running(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    inspected = subprocess.run(
        ["/bin/ps", "-p", str(pid), "-o", "stat="],
        capture_output=True,
        text=True,
        check=False,
    )
    state = inspected.stdout.strip()
    return inspected.returncode == 0 and bool(state) and not state.startswith("Z")


def wait_for_path(path, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.is_file():
            return
        time.sleep(0.02)
    raise AssertionError(f"Timed out waiting for {path}")


def install_live_camera_stub(runner, monkeypatch):
    def start_camera(run_dir, experiment):
        assert runner._acquire_runner_lock()
        (run_dir / ".camera-progress").write_text(
            "frame=1\nprogress=continue\n", encoding="utf-8"
        )
        state_path = run_dir / ".camera-process.json"
        marker = "c" * 32
        timeout = float(experiment["duration_seconds"]) + 30
        runner._write_launch_intent(
            state_path,
            marker=marker,
            kind="camera",
            experiment_id=experiment["id"],
            deadline_seconds=timeout,
        )
        return subprocess.Popen(
            [
                sys.executable,
                "-m",
                "hexapod_lab.deadline_exec",
                "--marker",
                marker,
                "--state-path",
                str(state_path),
                "--timeout-seconds",
                str(timeout),
                "--",
                sys.executable,
                "-c",
                "import time; time.sleep(60)",
            ],
            start_new_session=True,
            pass_fds=(runner.runner_lock_fd,),
        )

    monkeypatch.setattr(runner, "_start_camera", start_camera)


def test_service_stop_cannot_turn_truncated_simulation_into_success(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    item = store.create({"name": "interrupted", "duration_seconds": 5}, "test")
    claimed = store.claim_next()
    assert claimed and claimed["id"] == item["id"]
    runner = ExperimentRunner(store, configured(tmp_path))
    runner.stop_event.set()

    runner._execute(claimed)

    result = store.get(item["id"])
    assert result["status"] == "failed"
    assert "stopped before" in result["error"]
    assert result["evidence_sealed_at"]


def test_seal_failure_is_deferred_without_raising_from_execute(tmp_path, monkeypatch):
    store = Store(tmp_path / "lab.sqlite3")
    first = store.create({"name": "first", "duration_seconds": 0.01}, "test")
    second = store.create({"name": "second", "duration_seconds": 0.01}, "test")
    runner = ExperimentRunner(store, configured(tmp_path))
    original_finalize = store.finalize_evidence
    calls = 0

    def fail_once(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("simulated manifest failure")
        return original_finalize(*args, **kwargs)

    monkeypatch.setattr(store, "finalize_evidence", fail_once)
    runner._execute(store.claim_next())
    runner._execute(store.claim_next())

    assert store.get(first["id"])["status"] == "succeeded"
    assert store.get(first["id"])["evidence_sealed_at"] is None
    assert store.get(second["id"])["status"] == "succeeded"
    assert store.get(second["id"])["evidence_sealed_at"]


def test_command_cancellation_terminates_spawned_descendant(tmp_path, monkeypatch):
    store = Store(tmp_path / "lab.sqlite3")
    item = store.create({"name": "cancel process tree", "duration_seconds": 5}, "test")
    claimed = store.claim_next()
    assert claimed and claimed["id"] == item["id"]
    child_script = (
        "import os,pathlib,subprocess,sys,time;"
        "desc=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']);"
        "pathlib.Path(os.environ['HEXAPOD_RUN_DIR'],'descendant.pid').write_text(str(desc.pid));"
        "time.sleep(60)"
    )
    settings = configured(
        tmp_path,
        driver="command",
        robot_command=(sys.executable, "-c", child_script),
    )
    runner = ExperimentRunner(store, settings)
    install_live_camera_stub(runner, monkeypatch)
    worker = threading.Thread(target=runner._execute, args=(claimed,))
    descendant_pid = None
    try:
        worker.start()
        pid_path = tmp_path / "experiments" / item["id"] / "descendant.pid"
        wait_for_path(pid_path)
        descendant_pid = int(pid_path.read_text())
        assert process_is_running(descendant_pid)

        store.cancel(item["id"])
        worker.join(timeout=8)
        assert not worker.is_alive()
        assert store.get(item["id"])["status"] == "cancelled"
        deadline = time.monotonic() + 5
        while process_is_running(descendant_pid) and time.monotonic() < deadline:
            time.sleep(0.02)
        assert not process_is_running(descendant_pid)
    finally:
        runner.stop_event.set()
        if worker.is_alive():
            store.cancel(item["id"])
            worker.join(timeout=8)
        if descendant_pid and process_is_running(descendant_pid):
            try:
                os.kill(descendant_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


def test_command_environment_excludes_service_credentials(monkeypatch):
    monkeypatch.setenv("HEXAPOD_API_KEYS", "operator:someone:secret")
    monkeypatch.setenv("HEXAPOD_LAB_TOKEN", "secret")
    monkeypatch.setenv("UNRELATED_SECRET", "secret")
    environment = ExperimentRunner._command_environment()
    assert "HEXAPOD_API_KEYS" not in environment
    assert "HEXAPOD_LAB_TOKEN" not in environment
    assert "UNRELATED_SECRET" not in environment


def test_command_driver_refuses_simulation_only_backlog(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    item = store.create({
        "name": "simulation backlog after driver switch",
        "duration_seconds": 1,
        "parameters": {"simulation_only": True},
        "execution_mode": "builtin",
    }, "test")
    marker = tmp_path / "physical-command-started"
    runner = ExperimentRunner(store, configured(
        tmp_path,
        driver="command",
        robot_command=(
            sys.executable,
            "-c",
            f"from pathlib import Path; Path({str(marker)!r}).write_text('started')",
        ),
    ))

    runner._execute(store.claim_next())

    result = store.get(item["id"])
    assert result["status"] == "failed"
    assert "Simulation-only experiment refused" in result["error"]
    assert not marker.exists()


def test_camera_wrapper_gets_minimal_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("HEXAPOD_API_KEYS", "operator:someone:secret")
    monkeypatch.setenv("HEXAPOD_LAB_TOKEN", "secret")
    captured = {}

    class FakeProcess:
        returncode = None

        def poll(self):
            return None

    def fake_popen(command, **kwargs):
        captured["command"] = command
        captured["environment"] = kwargs["env"]
        return FakeProcess()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    runner = ExperimentRunner(
        Store(tmp_path / "lab.sqlite3"),
        configured(tmp_path, camera_input="camera-device"),
    )
    monkeypatch.setattr(runner, "_wait_for_camera_ready", lambda *_args: None)
    run_dir = tmp_path / "experiments" / "camera-test"
    run_dir.mkdir(parents=True)

    runner._start_camera(run_dir, {"id": "camera-test", "duration_seconds": 1})

    assert "hexapod_lab.deadline_exec" in captured["command"]
    assert "--state-path" in captured["command"]
    assert "HEXAPOD_API_KEYS" not in captured["environment"]
    assert "HEXAPOD_LAB_TOKEN" not in captured["environment"]


def test_restart_kills_guarded_group_after_wrapper_and_parent_sigkill(tmp_path):
    data_dir = tmp_path / "data"
    store = Store(data_dir / "lab.sqlite3")
    item = store.create(
        {"name": "crashed command", "duration_seconds": 0.15}, "test"
    )
    child_script = (
        "import json,os,pathlib,signal,subprocess,sys,time;"
        "signal.signal(signal.SIGTERM,signal.SIG_IGN);"
        "desc=subprocess.Popen([sys.executable,'-c',"
        "'import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(60)']);"
        "pathlib.Path(os.environ['HEXAPOD_RUN_DIR'],'guarded-pids.json').write_text("
        "json.dumps([os.getpid(),desc.pid]));time.sleep(60)"
    )
    harness = tmp_path / "runner_harness.py"
    harness.write_text(
        "from pathlib import Path\n"
        "from hexapod_lab.config import Settings\n"
        "from hexapod_lab.db import Store\n"
        "from hexapod_lab.runner import ExperimentRunner\n"
        f"data_dir = Path({str(data_dir)!r})\n"
        "store = Store(data_dir / 'lab.sqlite3')\n"
        "settings = Settings(data_dir=data_dir, api_keys='admin:a:b', "
        "driver='command', robot_command=("
        f"{sys.executable!r}, '-c', {child_script!r}), camera_input='', "
        "bind='127.0.0.1', port=8767, public_base_url='', auto_worker=False, "
        "max_duration_seconds=30, robot_command_shutdown_seconds=0.4)\n"
        "runner = ExperimentRunner(store, settings)\n"
        "claimed = store.claim_next()\n"
        "run_dir = data_dir / 'experiments' / claimed['id']\n"
        "run_dir.mkdir(parents=True, exist_ok=True)\n"
        "(run_dir / '.camera-progress').write_text('frame=1\\nprogress=continue\\n')\n"
        "class Camera:\n"
        "    def poll(self): return None\n"
        "runner._run_command(claimed, run_dir, Camera())\n",
        encoding="utf-8",
    )
    harness_process = subprocess.Popen([sys.executable, str(harness)])
    guarded_pids = []
    wrapper_pid = None
    try:
        run_dir = data_dir / "experiments" / item["id"]
        pid_path = run_dir / "guarded-pids.json"
        state_path = run_dir / ".robot-process.json"
        wait_for_path(pid_path)
        wait_for_path(state_path)
        guarded_pids = json.loads(pid_path.read_text())
        wrapper_pid = json.loads(state_path.read_text())["pid"]
        assert all(process_is_running(pid) for pid in guarded_pids)

        # Freeze the Lab-side runner, kill only the independent wrapper, and
        # verify its guarded command is still present until restart recovery
        # uses the persisted process-group identity.
        os.kill(harness_process.pid, signal.SIGSTOP)
        os.kill(wrapper_pid, signal.SIGKILL)
        deadline = time.monotonic() + 3
        while process_is_running(wrapper_pid) and time.monotonic() < deadline:
            time.sleep(0.02)
        assert not process_is_running(wrapper_pid)
        assert any(process_is_running(pid) for pid in guarded_pids)
        os.kill(harness_process.pid, signal.SIGKILL)
        harness_process.wait(timeout=5)

        recovered = ExperimentRunner(
            store,
            configured(
                data_dir,
                driver="command",
                robot_command=(sys.executable, "-c", "raise SystemExit(0)"),
            ),
        )
        recovered.start()
        assert recovered.thread is None
        deadline = time.monotonic() + 5
        while (
            any(process_is_running(pid) for pid in guarded_pids)
            and time.monotonic() < deadline
        ):
            time.sleep(0.02)
        assert not any(process_is_running(pid) for pid in guarded_pids)
        result = store.get(item["id"])
        assert result["status"] == "failed"
        assert "restarted while this experiment was running" in result["error"]
        assert result["evidence_sealed_at"]
        assert store.runner_safety_control()["latched"] is True
        recovered.stop()

        restarted = ExperimentRunner(store, configured(data_dir))
        restarted.start()
        assert restarted.thread is None
        store.resume_runner_safety("camera and robot inspected", created_by="test")
        restarted.start()
        assert restarted.thread is not None and restarted.thread.is_alive()
        restarted.stop()
    finally:
        if harness_process.poll() is None:
            harness_process.kill()
            harness_process.wait(timeout=5)
        for pid in guarded_pids:
            if process_is_running(pid):
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        if wrapper_pid and process_is_running(wrapper_pid):
            try:
                os.killpg(wrapper_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


def test_marker_only_launch_intent_is_fenced_before_any_new_claim(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    item = store.create({"name": "intent only", "duration_seconds": 1}, "test")
    claimed = store.claim_next()
    run_dir = tmp_path / "experiments" / item["id"]
    run_dir.mkdir(parents=True)
    runner = ExperimentRunner(store, configured(tmp_path))
    runner._write_launch_intent(
        run_dir / ".robot-process.json",
        marker="a" * 32,
        kind="robot-command",
        experiment_id=claimed["id"],
        deadline_seconds=31,
    )

    runner.start()

    assert runner.thread is None
    assert store.runner_safety_control()["latched"] is True
    assert store.get(item["id"])["status"] == "failed"
    recovered_state = json.loads((run_dir / ".robot-process.json").read_text())
    assert recovered_state["recovered_at"]
    runner.stop()


def test_process_wide_runner_lock_refuses_a_second_worker(tmp_path):
    path = tmp_path / "lab.sqlite3"
    first = ExperimentRunner(Store(path), configured(tmp_path))
    second = ExperimentRunner(Store(path), configured(tmp_path))
    try:
        first.start()
        assert first.thread is not None and first.thread.is_alive()
        try:
            second.start()
        except RuntimeError as error:
            assert "runner lock" in str(error)
        else:
            raise AssertionError("second runner unexpectedly acquired the singleton lock")
    finally:
        first.stop()
        second.stop()


def test_stop_retains_runner_lock_if_worker_cannot_join(tmp_path):
    runner = ExperimentRunner(
        Store(tmp_path / "lab.sqlite3"), configured(tmp_path)
    )
    assert runner._acquire_runner_lock()

    class StuckThread:
        alive = True

        def join(self, timeout):
            assert timeout == 12

        def is_alive(self):
            return self.alive

    stuck = StuckThread()
    runner.thread = stuck
    try:
        try:
            runner.stop()
        except RuntimeError as error:
            assert "lock retained" in str(error)
        else:
            raise AssertionError("stop unexpectedly released a live worker")
        assert runner.runner_lock_fd is not None
    finally:
        stuck.alive = False
        runner.stop()


def test_stop_fences_command_popen_before_active_process_publication(
    tmp_path, monkeypatch
):
    store = Store(tmp_path / "lab.sqlite3")
    item = store.create(
        {"name": "stop during launch", "duration_seconds": 5}, "test"
    )
    claimed = store.claim_next()
    runner = ExperimentRunner(
        store,
        configured(
            tmp_path,
            driver="command",
            robot_command=(sys.executable, "-c", "raise SystemExit(0)"),
        ),
    )
    assert runner._acquire_runner_lock()
    run_dir = tmp_path / "experiments" / item["id"]
    run_dir.mkdir(parents=True)
    (run_dir / ".camera-progress").write_text(
        "frame=1\nprogress=continue\n", encoding="utf-8"
    )

    class Camera:
        def poll(self):
            return None

    class FakeProcess:
        pid = 424242
        returncode = None
        terminated = False

        def communicate(self, _payload, timeout):
            assert timeout == 0.25
            if self.terminated:
                return (None, None)
            raise subprocess.TimeoutExpired("guarded", timeout)

    popen_entered = threading.Event()
    allow_popen = threading.Event()
    fake_process = FakeProcess()
    terminated = []

    def blocked_popen(*_args, **_kwargs):
        popen_entered.set()
        assert allow_popen.wait(timeout=5)
        return fake_process

    def terminate(process, _state_path=None):
        # Publication must happen before either stop() or the worker can sweep
        # the wrapper created by the fenced Popen.
        assert runner.active_process is process
        process.terminated = True
        process.returncode = -signal.SIGTERM
        terminated.append(process)
        return True

    monkeypatch.setattr(subprocess, "Popen", blocked_popen)
    monkeypatch.setattr(runner, "_terminate_command", terminate)
    errors = []

    def run_command():
        try:
            runner._run_command(claimed, run_dir, Camera())
        except Exception as error:
            errors.append(error)

    worker = threading.Thread(target=run_command)
    runner.thread = worker
    worker.start()
    assert popen_entered.wait(timeout=5)
    stopper = threading.Thread(target=runner.stop)
    stopper.start()
    time.sleep(0.05)
    assert stopper.is_alive()
    assert terminated == []
    allow_popen.set()
    stopper.join(timeout=5)
    worker.join(timeout=5)

    assert not stopper.is_alive()
    assert not worker.is_alive()
    assert terminated
    assert errors == []
    assert runner.runner_lock_fd is None


def test_unproven_robot_cleanup_latches_runner_before_next_claim(
    tmp_path, monkeypatch
):
    store = Store(tmp_path / "lab.sqlite3")
    first = store.create(
        {"name": "unkillable first", "duration_seconds": 1}, "test"
    )
    second = store.create(
        {"name": "must remain queued", "duration_seconds": 1}, "test"
    )
    runner = ExperimentRunner(
        store,
        configured(
            tmp_path,
            driver="command",
            robot_command=(sys.executable, "-c", "raise SystemExit(0)"),
        ),
    )

    class FakeProcess:
        pid = 424242
        returncode = 0

        def communicate(self, _payload, timeout):
            assert timeout == 0.25
            return (None, None)

        def poll(self):
            return self.returncode

    class Camera(FakeProcess):
        pass

    def start_camera(run_dir, _experiment):
        (run_dir / ".camera-progress").write_text(
            "frame=1\nprogress=continue\n", encoding="utf-8"
        )
        return Camera()

    monkeypatch.setattr(subprocess, "Popen", lambda *_args, **_kwargs: FakeProcess())
    monkeypatch.setattr(runner, "_start_camera", start_camera)
    monkeypatch.setattr(runner, "_terminate_command", lambda *_args: False)
    try:
        runner._execute(store.claim_next())
        assert store.get(first["id"])["status"] == "failed"
        assert store.runner_safety_control()["latched"] is True

        loop = threading.Thread(target=runner._loop)
        loop.start()
        loop.join(timeout=2)
        assert not loop.is_alive()
        assert store.get(second["id"])["status"] == "queued"
    finally:
        # This test models an OS-level cleanup failure without creating a real
        # process group; clear the fake latch solely to release the test lock.
        store.resume_runner_safety("test fake process removed", created_by="test")
        runner.stop()


def test_runner_safety_latch_is_visible_and_requires_operator_ack(tmp_path):
    settings = configured(
        tmp_path,
        auto_worker=True,
        api_keys="admin:alice:secret,viewer:bob:read-only",
    )
    app = create_app(settings)
    app.state.store.latch_runner_safety(
        "Recovered unfinished motion", created_by="test"
    )
    headers = {"Authorization": "Bearer secret"}
    with TestClient(app) as client:
        status = client.get("/api/runner-safety", headers=headers)
        assert status.status_code == 200
        assert status.json()["control"]["latched"] is True
        assert client.post(
            "/api/runner-safety/resume",
            headers={"Authorization": "Bearer read-only", "X-Hexapod-Lab": "1"},
            json={"reason": "viewer cannot resume", "robot_inspected": True},
        ).status_code == 403
        refused = client.post(
            "/api/runner-safety/resume",
            headers={**headers, "X-Hexapod-Lab": "1"},
            json={"reason": "looked", "robot_inspected": False},
        )
        assert refused.status_code == 422
        resumed = client.post(
            "/api/runner-safety/resume",
            headers={**headers, "X-Hexapod-Lab": "1"},
            json={"reason": "camera and robot inspected", "robot_inspected": True},
        )
        assert resumed.status_code == 202
        assert resumed.json()["control"]["latched"] is False
        assert resumed.json()["worker_active"] is True


def test_app_keeps_data_directory_private(tmp_path):
    create_app(configured(tmp_path))
    assert tmp_path.stat().st_mode & 0o777 == 0o700
    assert (tmp_path / "lab.sqlite3").stat().st_mode & 0o777 == 0o600


def test_runner_resume_response_reports_a_relatched_recovery(tmp_path, monkeypatch):
    settings = configured(tmp_path, auto_worker=True)
    app = create_app(settings)
    app.state.store.latch_runner_safety("initial recovery", created_by="test")
    headers = {"Authorization": "Bearer secret", "X-Hexapod-Lab": "1"}
    with TestClient(app) as client:
        monkeypatch.setattr(
            app.state.runner,
            "start",
            lambda: app.state.store.latch_runner_safety(
                "cleanup remains unresolved", created_by="experiment-runner"
            ),
        )
        resumed = client.post(
            "/api/runner-safety/resume",
            headers=headers,
            json={"reason": "inspected", "robot_inspected": True},
        )
        assert resumed.status_code == 202
        assert resumed.json()["control"]["latched"] is True
        assert "unresolved" in resumed.json()["control"]["reason"]
        assert resumed.json()["worker_active"] is False


def test_camera_startup_failure_prevents_robot_command(tmp_path, monkeypatch):
    store = Store(tmp_path / "lab.sqlite3")
    item = store.create({"name": "camera fails", "duration_seconds": 1}, "test")
    marker = tmp_path / "robot-started"
    runner = ExperimentRunner(store, configured(
        tmp_path,
        driver="command",
        robot_command=(
            sys.executable,
            "-c",
            f"from pathlib import Path; Path({str(marker)!r}).write_text('yes')",
        ),
    ))
    monkeypatch.setattr(
        runner,
        "_start_camera",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("camera unavailable")),
    )

    runner._execute(store.claim_next())

    assert store.get(item["id"])["status"] == "failed"
    assert not marker.exists()


def test_midrun_camera_loss_stops_robot_command(tmp_path, monkeypatch):
    store = Store(tmp_path / "lab.sqlite3")
    item = store.create({"name": "camera loss", "duration_seconds": 5}, "test")
    robot_pid_path = tmp_path / "robot.pid"
    robot_script = (
        "import os,pathlib,time;"
        f"pathlib.Path({str(robot_pid_path)!r}).write_text(str(os.getpid()));"
        "time.sleep(60)"
    )
    runner = ExperimentRunner(store, configured(
        tmp_path,
        driver="command",
        robot_command=(sys.executable, "-c", robot_script),
    ))
    camera_holder = {}

    def start_camera(run_dir, experiment):
        install_live_camera_stub(runner, monkeypatch)
        process = runner._start_camera(run_dir, experiment)
        camera_holder["process"] = process
        return process

    monkeypatch.setattr(runner, "_start_camera", start_camera)
    worker = threading.Thread(target=runner._execute, args=(store.claim_next(),))
    robot_pid = None
    try:
        worker.start()
        wait_for_path(robot_pid_path)
        robot_pid = int(robot_pid_path.read_text())
        camera = camera_holder["process"]
        os.killpg(camera.pid, signal.SIGTERM)
        worker.join(timeout=8)
        assert not worker.is_alive()
        result = store.get(item["id"])
        assert result["status"] == "failed"
        assert "Camera capture" in result["error"]
        deadline = time.monotonic() + 3
        while process_is_running(robot_pid) and time.monotonic() < deadline:
            time.sleep(0.02)
        assert not process_is_running(robot_pid)
    finally:
        runner.stop()
        if worker.is_alive():
            worker.join(timeout=5)
        if robot_pid and process_is_running(robot_pid):
            try:
                os.kill(robot_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


def test_manifest_hashes_artifacts_without_reading_whole_files(tmp_path, monkeypatch):
    (tmp_path / "telemetry.bin").write_bytes(b"x" * (2 * 1024 * 1024))

    def refuse_read_bytes(_path):
        raise AssertionError("manifest hashing must stream")

    monkeypatch.setattr(Path, "read_bytes", refuse_read_bytes)
    digest = ExperimentRunner._write_manifest(
        tmp_path,
        max_artifacts=2,
        max_total_bytes=3 * 1024 * 1024,
    )
    assert len(digest) == 64


def test_terminal_commit_retries_and_removes_recovery_marker(tmp_path, monkeypatch):
    store = Store(tmp_path / "lab.sqlite3")
    item = store.create({"name": "retry commit", "duration_seconds": 0.01}, "test")
    runner = ExperimentRunner(store, configured(tmp_path))
    original_finish = store.finish
    attempts = 0

    def flaky_finish(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise OSError("temporary sqlite failure")
        return original_finish(*args, **kwargs)

    monkeypatch.setattr(store, "finish", flaky_finish)
    runner._execute(store.claim_next())

    assert attempts == 3
    assert store.get(item["id"])["status"] == "succeeded"
    assert not list((tmp_path / "experiments" / item["id"]).glob("*.pending.json"))


def test_service_stop_synchronously_kills_term_ignoring_command_group(
    tmp_path, monkeypatch
):
    store = Store(tmp_path / "lab.sqlite3")
    item = store.create({"name": "shutdown process tree", "duration_seconds": 30}, "test")
    child_script = (
        "import os,pathlib,signal,subprocess,sys,time;"
        "signal.signal(signal.SIGTERM,signal.SIG_IGN);"
        "desc=subprocess.Popen([sys.executable,'-c',"
        "'import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(60)']);"
        "pathlib.Path(os.environ['HEXAPOD_RUN_DIR'],'stop-descendant.pid').write_text(str(desc.pid));"
        "time.sleep(60)"
    )
    runner = ExperimentRunner(store, configured(
        tmp_path,
        driver="command",
        robot_command=(sys.executable, "-c", child_script),
    ))
    install_live_camera_stub(runner, monkeypatch)
    descendant_pid = None
    try:
        runner.start()
        pid_path = tmp_path / "experiments" / item["id"] / "stop-descendant.pid"
        wait_for_path(pid_path)
        descendant_pid = int(pid_path.read_text())
        runner.stop()
        assert runner.thread is not None and not runner.thread.is_alive()
        deadline = time.monotonic() + 3
        while process_is_running(descendant_pid) and time.monotonic() < deadline:
            time.sleep(0.02)
        assert not process_is_running(descendant_pid)
    finally:
        runner.stop()
        if descendant_pid and process_is_running(descendant_pid):
            try:
                os.kill(descendant_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
