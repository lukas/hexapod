"""Compile the production loop with fake IO to check acquisition scheduling.

This is a host scheduler regression, not an Arduino build or a bus timing test.
The parser stub represents one completed S request; servo/IMU passes are instant.
It cannot establish physical feedback freshness or worst-case pass latency.
"""

from pathlib import Path
import re
import shutil
import subprocess

import pytest


FIRMWARE = Path(__file__).resolve().parents[1] / "feetech_bridge" / "feetech_bridge.ino"

STUBS = r"""
#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>
using u8 = uint8_t;
unsigned long clockMs = 1000, fbStampMs = 1000, posStampMs = 1000;
unsigned long lastHostMs = 1000, hostSLastMs = 0, hostSRefreshAtMs = 0;
unsigned long dbgDesyncResets = 0, dbgHostBytesSeen = 0;
unsigned long dbgHostSnapshotAsyncRefreshes = 0;
bool streaming = true, hostSeen = true, autoLimped = false;
bool hostSRefreshPending = false;
int parkedKind = 0, binState = 0, posSeq = 0;
const int ID_LO = 1, ID_HI = 18;
int fullCount = 0, fastCount = 0, imuCount = 0;
std::vector<unsigned long> fullTimes{1000};
std::vector<std::string> events;
unsigned long millis() { return clockMs; }
struct SerialMock {
  int remaining = 0;
  int available() { return remaining; }
  int read() { --remaining; return 'S'; }
} Serial1;
void execParked() { events.push_back("parked"); parkedKind = 0; }
void replyErr() { events.push_back("error"); }
void feedHostByte(uint8_t) {
  events.push_back("request");
  hostSLastMs = clockMs;
  hostSRefreshAtMs = clockMs + HOST_S_REFRESH_DELAY_MS;
  hostSRefreshPending = true;
}
void streamFullPass() {
  events.push_back("full"); ++fullCount;
  fbStampMs = posStampMs = clockMs; ++posSeq;
  fullTimes.push_back(clockMs);
}
void streamFastPass() {
  events.push_back("fast"); ++fastCount;
  posStampMs = clockMs; ++posSeq;
}
void streamImuPass() { events.push_back("imu"); ++imuCount; }
void refreshSnapshotNow() { streamFastPass(); streamImuPass(); }
namespace tft {
void bootTick(unsigned long) {}
void hostLostTick(unsigned long) {}
void autoLimpPaint() {}
}
struct StsMock { void EnableTorque(u8, int) {} } sts;
"""

MAIN = r"""
int main(int argc, char **argv) {
  const std::string mode = argv[1];
  if (mode == "periodic") {
    const unsigned long period = 1000 / std::atoi(argv[2]);
    for (; clockMs < 3000; ++clockMs) {
      if ((clockMs - 1000) % period == 0) ++Serial1.remaining;
      loop();
    }
    unsigned long maxGap = clockMs - fullTimes.back();
    for (size_t i = 1; i < fullTimes.size(); ++i)
      maxGap = std::max(maxGap, fullTimes[i] - fullTimes[i-1]);
    std::cout << fullCount << " " << maxGap << " " << posSeq;
    return 0;
  }
  clockMs = 1100;
  if (mode == "quiet_due") hostSLastMs = 1099;
  if (mode == "pending_due" || mode == "pending_fresh") {
    hostSLastMs = 1099;
    hostSRefreshPending = true;
    hostSRefreshAtMs = 1100;
    if (mode == "pending_fresh") fbStampMs = 1090;
  }
  if (mode == "parked") { parkedKind = 1; Serial1.remaining = 1; }
  if (mode == "incomplete") binState = 1;
  lastHostMs = clockMs;
  loop();
  for (const auto &event : events) std::cout << event << " ";
  std::cout << "seq=" << posSeq;
}
"""


@pytest.fixture(scope="module")
def schedulers(tmp_path_factory):
    compiler = shutil.which("clang++") or shutil.which("c++")
    if compiler is None:
        pytest.skip("A C++ compiler is required for the production-loop regression")
    source = FIRMWARE.read_text()
    # loop is the last function in the sketch; compile it verbatim.
    loop = source[source.index("void loop() {"):]
    constants = []
    for name in ("FB_PERIOD_MS", "HOST_S_CONTROL_IDLE_MS", "HOST_S_REFRESH_DELAY_MS", "HOST_BIN_DESYNC_MS",
                 "HOST_LOST_MS", "HOST_LIMP_MS"):
        declaration = re.search(rf"static const unsigned long {name}\s*=\s*[^;]+;", source)
        assert declaration is not None, name
        constants.append(declaration.group())
    # Negative control removes only the two scheduler fixes, keeping the same
    # production loop and IO stubs. It must reproduce the previous starvation.
    old_loop, replacements = re.subn(
        r"    if \(now - fbStampMs >= FB_PERIOD_MS\) \{\n"
        r"      streamFullPass\(\);\n    \} else \{\n"
        r"      streamFastPass\(\);\n    \}\n    streamImuPass\(\);",
        "    refreshSnapshotNow();", loop, count=1,
    )
    assert replacements == 1
    old_loop = old_loop.replace(
        " < HOST_S_CONTROL_IDLE_MS\n      && now - fbStampMs < FB_PERIOD_MS)",
        " < HOST_S_CONTROL_IDLE_MS)",
    )
    directory = tmp_path_factory.mktemp("firmware_scheduler")
    executables = {}
    for name, body in (("production", loop), ("before_fix", old_loop)):
        cpp = directory / f"{name}.cpp"
        executable = directory / name
        cpp.write_text("\n".join(constants) + STUBS + body + MAIN)
        subprocess.run([compiler, "-std=c++17", "-O0", str(cpp), "-o", str(executable)],
                       check=True, capture_output=True, text=True)
        executables[name] = executable
    return executables


def run(schedulers, *args, variant="production"):
    return subprocess.check_output(
        [str(schedulers[variant]), *map(str, args)], text=True,
    ).strip()


@pytest.mark.parametrize("hz", [10, 20, 50, 100])
def test_repeated_snapshots_do_not_starve_full_health(schedulers, hz):
    count, max_gap_ms, position_seq = map(int, run(schedulers, "periodic", hz).split())
    assert count >= 19
    assert max_gap_ms <= 102  # 100 ms due period plus simulated host dispatch.
    assert position_seq >= count


@pytest.mark.parametrize("hz", [50, 100])
def test_same_harness_reproduces_previous_starvation(schedulers, hz):
    count, max_gap_ms, _ = map(int, run(schedulers, "periodic", hz, variant="before_fix").split())
    assert count == 0
    assert max_gap_ms == 2000


@pytest.mark.parametrize("mode,expected", [
    ("pending_due", "full imu seq=1"),
    ("pending_fresh", "fast imu seq=1"),
    ("quiet_due", "full seq=1"),
    ("parked", "parked request seq=0"),
    ("incomplete", "seq=0"),
])
def test_refresh_selection_and_host_priority(schedulers, mode, expected):
    assert run(schedulers, mode) == expected
