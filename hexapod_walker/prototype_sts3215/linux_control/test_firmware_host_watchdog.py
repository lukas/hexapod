"""Execute the sketch's actual clock/control branches with no robot attached."""
from pathlib import Path
import re
import shutil
import subprocess

import pytest


SKETCH = (Path(__file__).resolve().parents[1] / "firmware" /
          "feetech_bridge" / "feetech_bridge.ino")


def _function(source, signature):
    start = source.index(signature)
    return source[start:source.index("\n}\n", start) + 3]


@pytest.fixture(scope="module")
def watchdog_program(tmp_path_factory):
    source = SKETCH.read_text()
    constants = "\n".join(re.search(
        rf"^static const [^\n]+\b{name} = [^;]+;", source, re.M).group()
        for name in ("ID_LO", "ID_HI", "FB_PERIOD_MS", "HOST_LOST_MS",
                     "HOST_LIMP_MS", "HOST_BIN_DESYNC_MS",
                     "HOST_S_CONTROL_IDLE_MS"))
    # The Uno Q MCU uses 32-bit long. Use that width explicitly on hosts
    # whose native unsigned long is 64-bit, including this Mac's compiler.
    code = (constants + "\n" + _function(source, "static void hostPump() {")
            + "\n" + _function(source, "void loop() {"))
    code = code.replace("unsigned long", "uint32_t").replace("(long)", "(int32_t)")
    harness = r'''
#include <cassert>
#include <cstdint>
#include <string>
#include <vector>
using u8 = uint8_t;
static uint32_t clock_ms, lastHostMs, hostSRefreshAtMs, hostSLastMs, fbStampMs;
static uint32_t dbgHostBytesSeen, dbgDesyncResets, dbgHostSnapshotAsyncRefreshes;
static bool hostSeen = true, autoLimped, streaming, hostSRefreshPending;
static uint8_t parkedKind, binState;
static bool inject_partial, inject_parked_partial;
static unsigned errors, warnings, limp_paints, passes;
uint32_t millis() { return clock_ms; }
struct HostSerial {
  std::vector<uint8_t> rx;
  int available() { return rx.size(); }
  int read() { auto b = rx.front(); rx.erase(rx.begin()); return b; }
  void flush() {}
} Serial1;
struct Servos {
  std::vector<int> off;
  void EnableTorque(u8 id, int enabled) { assert(enabled == 0); off.push_back(id); }
} sts;
namespace tft {
  void bootTick(uint32_t) {}
  void hostLostTick(uint32_t) { ++warnings; }
  void autoLimpPaint() { ++limp_paints; }
}
void replyErr() { ++errors; }
void feedHostByte(uint8_t b) { if (b == 0xa5) binState = 1; }
static void hostPump();
void execParked() {
  parkedKind = 0;
  if (inject_parked_partial) {
    clock_ms += 3;
    Serial1.rx.push_back(0xa5);
    hostPump();
  }
}
void streamPass() {
  ++passes;
  clock_ms += 3;
  if (inject_partial) {
    Serial1.rx.push_back('R'); // No newline: no completed/parked command.
    hostPump();
  }
}
void streamFastPass() { streamPass(); }
void streamFullPass() { streamPass(); }
void streamImuPass() {}
'''
    main = r'''
int main(int argc, char **argv) {
  assert(argc == 2);
  const std::string name = argv[1];
  clock_ms = 1000;
  lastHostMs = 999;
  if (name == "partial_fast" || name == "partial_full" || name == "partial_rollover") {
    streaming = inject_partial = true;
    if (name == "partial_rollover") clock_ms = UINT32_MAX - 1;
    fbStampMs = name == "partial_full" ? clock_ms - 1000 : clock_ms;
    loop();
    assert(passes == 1 && lastHostMs == clock_ms && !autoLimped);
    assert(sts.off.empty() && warnings == 0 && errors == 0);
  } else if (name == "parked_partial" || name == "parked_rollover") {
    if (name == "parked_rollover") clock_ms = UINT32_MAX - 1;
    parkedKind = 1;
    inject_parked_partial = true;
    loop();
    assert(lastHostMs == clock_ms && binState == 1);
    assert(dbgDesyncResets == 0 && errors == 0 && sts.off.empty());
  } else if (name == "true_desync") {
    binState = 1;
    lastHostMs = clock_ms - 11;
    loop();
    assert(binState == 0 && dbgDesyncResets == 1 && errors == 1);
    assert(sts.off.empty());
  } else {
    uint32_t elapsed = name == "warn" ? 12001 :
                       name.find("limit") == 0 ? 30000 :
                       name.find("quiet") == 0 ? 12000 : 30001;
    // The rollover cases' host timestamp precedes UINT32_MAX and now follows it.
    clock_ms = name.find("rollover") != std::string::npos ? 5 : 50000;
    lastHostMs = clock_ms - elapsed;
    loop();
    if (elapsed > 30000) {
      assert(autoLimped && sts.off.size() == 18 && limp_paints == 1);
      for (int i = 0; i < 18; ++i) assert(sts.off[i] == i + 2);
      loop();
      assert(sts.off.size() == 18); // Still one cutoff per host-loss episode.
    } else {
      assert(!autoLimped && sts.off.empty());
    }
    assert(warnings == (elapsed > 12000 && clock_ms >= 1000 ? 1u : 0u));
  }
}
'''
    work = tmp_path_factory.mktemp("firmware-watchdog")
    cpp, binary = work / "watchdog.cpp", work / "watchdog"
    cpp.write_text(harness + code + main)
    compiler = shutil.which("c++")
    assert compiler, "A C++ compiler is required for the firmware mechanics regression"
    subprocess.run([compiler, "-std=c++11", str(cpp), "-o", str(binary)],
                   check=True, capture_output=True, text=True, timeout=4)
    return binary


@pytest.mark.parametrize("scenario", [
    "partial_fast", "partial_full", "partial_rollover", "parked_partial",
    "parked_rollover", "true_desync", "quiet", "warn", "limit", "lost",
    "lost_rollover", "limit_rollover", "quiet_rollover",
])
def test_host_clock_after_pumped_bytes(watchdog_program, scenario, monkeypatch):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh")
    subprocess.run([str(watchdog_program), scenario], check=True,
                   capture_output=True, text=True, timeout=1)
