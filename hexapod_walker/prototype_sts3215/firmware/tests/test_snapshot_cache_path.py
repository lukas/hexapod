"""Compile the production host-snapshot preparation path with fake IO.

The combined S command must remain cache-only during streaming once both
caches have been populated.  In particular, a stale IMU sample cannot make
each host tick repeat the 18-servo position transaction.
"""

from pathlib import Path
import re
import shutil
import subprocess

import pytest


FIRMWARE = Path(__file__).resolve().parents[1] / "feetech_bridge" / "feetech_bridge.ino"


def _extract_function(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for offset in range(brace, len(source)):
        if source[offset] == "{":
            depth += 1
        elif source[offset] == "}":
            depth -= 1
            if depth == 0:
                return source[start : offset + 1]
    raise AssertionError(f"unterminated function: {signature}")


@pytest.fixture(scope="module")
def snapshot_harness(tmp_path_factory):
    compiler = shutil.which("clang++") or shutil.which("c++")
    if compiler is None:
        pytest.skip("A C++ compiler is required for the firmware regression")

    source = FIRMWARE.read_text()
    declarations = []
    for name in ("HOST_S_REFRESH_DELAY_MS", "HOST_S_MAX_CACHE_AGE_MS"):
        declaration = re.search(
            rf"static const unsigned long {name}\s*=\s*[^;]+;", source
        )
        assert declaration is not None, name
        declarations.append(declaration.group())
    functions = [
        _extract_function(source, "static void scheduleHostSnapshotRefresh() {"),
        _extract_function(source, "static void prepareSnapshotForHost() {"),
    ]
    stubs = r"""
#include <cstdint>
#include <iostream>
#include <string>

static unsigned long clockMs = 1000;
static unsigned long posStampMs = 1000;
static unsigned long imuStampMs = 1000;
static unsigned long hostSLastMs = 0;
static unsigned long hostSRefreshAtMs = 0;
static bool streaming = true;
static bool imuCacheValid = true;
static bool hostSRefreshPending = false;
static uint32_t dbgHostSnapshotRequests = 0;
static uint32_t dbgHostSnapshotCacheHits = 0;
static uint32_t dbgHostSnapshotSyncRefreshes = 0;
static uint32_t dbgHostSnapshotSyncPosRefreshes = 0;
static uint32_t dbgHostSnapshotSyncImuRefreshes = 0;
static uint32_t dbgHostSnapshotStaleCacheReplies = 0;
static unsigned int fastPasses = 0;
static unsigned int imuPasses = 0;
static unsigned int fullRefreshes = 0;
static unsigned int posSeq = 41;

static unsigned long millis() { return clockMs; }
static void streamFastPass() {
  ++fastPasses;
  ++posSeq;
  posStampMs = clockMs;
}
static void streamImuPass() { ++imuPasses; }
static void refreshSnapshotNow() {
  ++fullRefreshes;
  streamFastPass();
  streamImuPass();
}
"""
    main = r"""
int main(int argc, char **argv) {
  const std::string mode = argv[1];
  int requests = 1;
  if (mode == "fresh") clockMs = 1010;
  if (mode == "stale_imu") {
    clockMs = 1020;
    posStampMs = 1015;
    imuStampMs = 1000;
    requests = 5;
  }
  if (mode == "missing_imu") {
    clockMs = 1005;
    imuCacheValid = false;
  }
  if (mode == "missing_pos") {
    clockMs = 1005;
    posStampMs = 0;
  }
  if (mode == "nonstreaming") {
    clockMs = 1005;
    streaming = false;
  }
  for (int i = 0; i < requests; ++i) {
    prepareSnapshotForHost();
    ++clockMs;
  }
  std::cout << fastPasses << " " << imuPasses << " " << fullRefreshes
            << " " << posSeq << " " << dbgHostSnapshotRequests
            << " " << dbgHostSnapshotCacheHits
            << " " << dbgHostSnapshotSyncRefreshes
            << " " << dbgHostSnapshotSyncPosRefreshes
            << " " << dbgHostSnapshotSyncImuRefreshes
            << " " << dbgHostSnapshotStaleCacheReplies
            << " " << hostSRefreshPending;
}
"""
    directory = tmp_path_factory.mktemp("firmware_snapshot_cache")
    cpp = directory / "snapshot_cache.cpp"
    executable = directory / "snapshot_cache"
    cpp.write_text("\n".join((*declarations, stubs, *functions, main)))
    subprocess.run(
        [compiler, "-std=c++17", "-O0", str(cpp), "-o", str(executable)],
        check=True,
        capture_output=True,
        text=True,
    )
    return executable


def _run(executable: Path, mode: str) -> list[int]:
    return list(
        map(int, subprocess.check_output([str(executable), mode], text=True).split())
    )


def test_fresh_streaming_snapshot_is_a_cache_hit(snapshot_harness):
    assert _run(snapshot_harness, "fresh") == [0, 0, 0, 41, 1, 1, 0, 0, 0, 0, 1]


def test_stale_imu_never_repeats_servo_reads_in_host_path(snapshot_harness):
    assert _run(snapshot_harness, "stale_imu") == [0, 0, 0, 41, 5, 0, 0, 0, 0, 5, 1]


@pytest.mark.parametrize(
    "mode,expected",
    [
        ("missing_imu", [0, 0, 0, 41, 1, 0, 0, 0, 0, 1, 1]),
        ("missing_pos", [1, 0, 0, 42, 1, 0, 1, 1, 0, 0, 1]),
        ("nonstreaming", [1, 1, 1, 42, 1, 0, 1, 1, 1, 0, 0]),
    ],
)
def test_only_missing_streaming_component_is_synchronously_refreshed(
    snapshot_harness, mode, expected
):
    assert _run(snapshot_harness, mode) == expected
