"""Exercise the production streaming-IMU failure state machine on the host."""

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
def imu_harness(tmp_path_factory):
    compiler = shutil.which("clang++") or shutil.which("c++")
    if compiler is None:
        pytest.skip("A C++ compiler is required for the firmware regression")

    source = FIRMWARE.read_text()
    limit = re.search(
        r"static const uint8_t STREAM_IMU_READ_FAIL_LIMIT\s*=\s*\d+;", source
    )
    assert limit is not None
    function = _extract_function(source, "static void streamImuPassInner() {")
    stubs = r"""
#include <cstdint>
#include <iostream>
#include <string>

static const uint8_t MPU_REG_ACCEL_XOUT_H = 0x3B;
static bool mpuReady = true;
static unsigned long imuRetryMs = 0;
static uint8_t streamImuReadFailStreak = 0;
static uint32_t dbgStreamImuReadFailures = 0;
static int16_t imuCache[7] = {};
static bool imuCacheValid = false;
static unsigned long imuStampMs = 0;
static unsigned long clockMs = 2000;
static bool dataReadOk = true;
static bool ensureOk = true;
static unsigned int ensureCalls = 0;
static unsigned int dataReadCalls = 0;

static unsigned long millis() { return clockMs; }
static uint8_t mpuEnsureReady() {
  ++ensureCalls;
  mpuReady = ensureOk;
  return ensureOk ? 0x68 : 0;
}
static bool mpuReadRegs(uint8_t, uint8_t *raw, uint8_t n) {
  ++dataReadCalls;
  if (!dataReadOk) return false;
  for (uint8_t i = 0; i < n; ++i) raw[i] = 0;
  return true;
}
static int16_t be16(const uint8_t *p) {
  return static_cast<int16_t>((static_cast<uint16_t>(p[0]) << 8) | p[1]);
}
"""
    main = r"""
int main(int argc, char **argv) {
  const std::string events = argv[1];
  for (char event : events) {
    if (event == 'j') {
      clockMs += 1001;
      continue;
    }
    dataReadOk = event == '1';
    streamImuPassInner();
    clockMs += 10;
  }
  std::cout << mpuReady << " " << static_cast<int>(streamImuReadFailStreak)
            << " " << dbgStreamImuReadFailures << " " << ensureCalls
            << " " << dataReadCalls << " " << imuStampMs
            << " " << imuCacheValid << " " << imuRetryMs;
}
"""
    directory = tmp_path_factory.mktemp("firmware_imu_debounce")
    cpp = directory / "imu_debounce.cpp"
    executable = directory / "imu_debounce"
    cpp.write_text("\n".join((stubs, limit.group(), function, main)))
    subprocess.run(
        [compiler, "-std=c++17", "-O0", str(cpp), "-o", str(executable)],
        check=True,
        capture_output=True,
        text=True,
    )
    return executable


def _run(executable: Path, events: str) -> list[int]:
    return list(
        map(
            int,
            subprocess.check_output([str(executable), events], text=True).split(),
        )
    )


@pytest.mark.parametrize("events,failures", [("01", 1), ("001", 2)])
def test_transient_failures_retry_without_reinitializing(imu_harness, events, failures):
    ready, streak, total_fails, ensure_calls, data_reads, stamp, valid, retry = _run(
        imu_harness, events
    )
    assert (ready, streak, total_fails, ensure_calls) == (1, 0, failures, 0)
    assert data_reads == len(events)
    assert stamp > 0 and valid == 1
    assert retry == 0


def test_three_consecutive_failures_enter_absent_sensor_backoff(imu_harness):
    ready, streak, failures, ensure_calls, data_reads, stamp, valid, retry = _run(
        imu_harness, "0000"
    )
    assert (ready, streak, failures, ensure_calls, data_reads) == (0, 0, 3, 0, 3)
    assert stamp == 0 and valid == 0
    assert retry > 0


def test_sensor_is_reinitialized_after_the_existing_backoff(imu_harness):
    ready, streak, failures, ensure_calls, data_reads, stamp, valid, retry = _run(
        imu_harness, "000j1"
    )
    assert (ready, streak, failures, ensure_calls, data_reads) == (1, 0, 3, 1, 4)
    assert stamp >= retry > 2000 and valid == 1
