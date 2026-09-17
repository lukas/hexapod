"""Run the production sketch with fake UART/servo IO; no hardware is touched.

These checks cover the actual parser, full-feedback acquisition and cooldown
interlock. They cannot verify physical torque removal or servo-bus timing.
"""

from pathlib import Path
import re
import shutil
import subprocess

import pytest


SKETCH = Path(__file__).resolve().parents[1] / "feetech_bridge" / "feetech_bridge.ino"

IO = r"""
#include <cassert>
#include <cstdint>
#include <cstring>
#include <deque>
#include <sstream>
#include <string>
#include <vector>
using u8 = uint8_t;
using u16 = uint16_t;
using s16 = int16_t;
struct __FlashStringHelper {};
#define F(s) reinterpret_cast<const __FlashStringHelper *>(s)
#define HEX 16
#define SMS_STS_PRESENT_POSITION_L 56
#define SMS_STS_TORQUE_ENABLE 40
unsigned long clockMs = 1000;
unsigned long millis() { return clockMs; }
unsigned long micros() { return clockMs * 1000; }
void delay(unsigned long ms) { clockMs += ms; }
struct SerialMock {
  std::deque<uint8_t> input;
  std::string output;
  void begin(unsigned long) {}
  int available() { return input.size(); }
  int read() { int v = input.front(); input.pop_front(); return v; }
  void flush() {}
  void write(uint8_t v) { output += static_cast<char>(v); }
  void print(const __FlashStringHelper *v) {
    output += reinterpret_cast<const char *>(v);
  }
  template<class T> void print(T v) { std::ostringstream s; s << v; output += s.str(); }
  template<class T> void print(T v, int) { print(v); }
  void println() { output += '\n'; }
  template<class T> void println(T v) { print(v); println(); }
  template<class T> void println(T v, int) { println(v); }
} Serial, Serial1;
struct WireMock {
  void begin() {}
  void setClock(int) {}
  void beginTransmission(uint8_t) {}
  void write(uint8_t) {}
  int endTransmission(bool = true) { return 1; }
  int requestFrom(uint8_t, uint8_t) { return 0; }
  int read() { return 0; }
} Wire;
namespace tft {
void bootSplash() {}
void bootTick(unsigned long) {}
void hostLostTick(unsigned long) {}
void autoLimpPaint() {}
void reinit() {}
void selfTest() {}
void pushJob(const char *) {}
void pushPanel(const char *, int *, int, long, int, int) {}
}
struct SMS_STS {
  SerialMock *pSerial = nullptr;
  unsigned long IOTimeOut = 100;
  uint8_t temp[254] = {};
  bool missing[254] = {}, torque[254] = {};
  bool dropStop = false;
  int lastId = 2, readLen = 15, motionWrites = 0, registerWrites = 0;
  int enableWrites = 0, stopPackets = 0;
  SMS_STS() { for (int id = 2; id <= 19; id++) temp[id] = 30; }
  void syncReadBegin(int, int, unsigned long) {}
  void syncReadEnd() {}
  void syncReadPacketTx(uint8_t *, int, int, int len) { readLen = len; }
  int syncReadPacketRx(int id, uint8_t *rx) {
    if (missing[id]) return 0;
    std::memset(rx, 0, readLen);
    if (readLen == 15) { rx[6] = 114; rx[7] = temp[id]; }
    return readLen;
  }
  int FeedBack(int id) { lastId = id; return missing[id] ? -1 : 15; }
  int getLastError() { return 0; }
  int Ping(int id) { return id; }
  int ReadPos(int) { return 0; }
  int ReadSpeed(int) { return 0; }
  int ReadLoad(int) { return 0; }
  int ReadMove(int) { return 0; }
  int ReadCurrent(int) { return 0; }
  int ReadVoltage(int) { return 114; }
  int ReadTemper(int id) { return temp[id < 0 ? lastId : id]; }
  int readByte(uint8_t, uint8_t) { return 0; }
  int readWord(uint8_t, uint8_t) { return 0; }
  int writeByte(uint8_t id, uint8_t addr, uint8_t v) {
    ++registerWrites;
    if (addr == SMS_STS_TORQUE_ENABLE) torque[id] = v != 0;
    return 1;
  }
  int writeWord(uint8_t, uint8_t, uint16_t) { ++registerWrites; return 1; }
  int EnableTorque(uint8_t id, uint8_t v) {
    if (v) ++enableWrites;
    torque[id] = v != 0; return 1;
  }
  int unLockEprom(uint8_t) { ++registerWrites; return 1; }
  int LockEprom(uint8_t) { return 1; }
  int WritePosEx(uint8_t, int16_t, uint16_t, uint8_t) { ++motionWrites; return 1; }
  void SyncWritePosEx(uint8_t *, int, int16_t *, uint16_t *, uint8_t *) {
    ++motionWrites;
  }
  void syncWrite(uint8_t *ids, uint8_t n, uint8_t addr, uint8_t *values, uint8_t len) {
    assert(addr == SMS_STS_TORQUE_ENABLE && len == 1 && n == 18);
    ++stopPackets;
    for (int k = 0; k < n; k++) {
      assert(ids[k] == k + 2 && values[k] == 0);
      if (!dropStop) torque[ids[k]] = false;
    }
  }
};
"""

CASES = r"""
void acquire(int temp, int id = 4) {
  clockMs += 100;
  sts.temp[id] = temp;
  streamFullPass();
}
void command(const std::string &s) {
  Serial1.output.clear();
  for (char c : s + "\n") feedHostByte(c);
}
void binary(char cmd, int n) {
  Serial1.output.clear();
  std::vector<uint8_t> frame{0xA5, 0x5A, uint8_t(cmd), uint8_t(n)};
  if (n) frame.insert(frame.end(), {4, 0, 8, 100, 0, 10});
  uint8_t checksum = 0;
  for (size_t i = 2; i < frame.size(); i++) checksum ^= frame[i];
  frame.push_back(checksum);
  for (uint8_t b : frame) feedHostByte(b);
}
void ready() {
  acquire(30); acquire(30); acquire(30);
  assert(!thermalBlocked());
  for (int id = 2; id <= 19; id++) sts.torque[id] = true;
}
void hot() {
  acquire(51); acquire(51); acquire(51);
  assert(thermalBlocked());
}
void refused() {
  assert(Serial1.output.find("ERR THERMAL_COOLDOWN") == 0);
}
int main(int argc, char **argv) {
  std::string mode = argv[1];
  if (mode == "boot") {
    command("TA 1"); refused();
    acquire(51); acquire(51); acquire(51);
    command("WP 4 2048 100 10"); refused();
    acquire(45); acquire(45); acquire(45);
    assert(!thermalBlocked() && !sts.torque[4]);
    return 0;
  }
  ready();
  if (mode == "confirmation") {
    for (int t : {90, 30, 51, 50, 51}) acquire(t);
    sts.missing[4] = true; acquire(51); sts.missing[4] = false;
    acquire(51); acquire(51);
    assert(!thermalBlocked());
    acquire(51);
    assert(thermalBlocked());
    for (int id = 2; id <= 19; id++) assert(!sts.torque[id]);
    acquire(46); acquire(46); acquire(46);
    assert(thermalBlocked());
    acquire(45); acquire(45);
    assert(thermalBlocked());
    sts.missing[4] = true; acquire(45); sts.missing[4] = false;
    acquire(45); acquire(45);
    assert(thermalBlocked());
    acquire(45);
    assert(!thermalBlocked() && !sts.torque[4]);
  } else if (mode == "freshness") {
    streaming = true;
    acquire(60);
    for (int i = 0; i < 100; i++) cmdBulkFeedback(0, nullptr);
    for (int i = 0; i < 10; i++) command("STREAM 1");
    assert(!thermalBlocked());
    acquire(60); assert(!thermalBlocked());
    acquire(60); assert(thermalBlocked());
  } else if (mode == "bypasses") {
    hot();
    for (const char *s : {"T 4 1", "TA 1", "WP 4 2048 100 10",
        "SW 1 4 2048 100 10", "W1 4 40 1", "W1 4 42 0", "W2 4 48 1000",
        "W2 4 39 256", "UL 4"}) {
      command(s); refused();
    }
    binary('W', 1); refused();
    binary('S', 1); refused();
    assert(sts.motionWrites == 0 && sts.enableWrites == 0 && sts.registerWrites == 0);
    command("DBG RESET");
    assert(Serial1.output.find("thermal_cooldown_mask=4") != std::string::npos);
    command("STREAM 0"); command("STREAM 1"); command("HELLO");
    assert(thermalBlocked());
    for (const char *s : {"T 4 0", "TA 0", "W1 4 40 0", "R1 4 63"}) {
      command(s); assert(Serial1.output.find("OK") == 0);
    }
    binary('F', 0); assert(Serial1.output[2] == 'f');
    binary('S', 0); assert(Serial1.output[2] == 's');
    acquire(45); acquire(45); acquire(45);
    assert(!thermalBlocked() && sts.motionWrites == 0 && sts.enableWrites == 0);
    command("TA 1"); assert(sts.enableWrites == 18);
    binary('W', 1); binary('S', 1); assert(sts.motionWrites == 2);
  } else if (mode == "multiple") {
    // Confirmation belongs to the same motor, not three different motors.
    for (int id : {4, 5, 6}) {
      for (int j : {4, 5, 6}) sts.temp[j] = 30;
      acquire(60, id);
    }
    assert(!thermalBlocked());
    sts.temp[6] = 30; sts.temp[5] = 60;
    hot();
    acquire(45); acquire(45); acquire(45);
    assert(thermalBlocked());
    sts.missing[5] = true;
    for (int i = 0; i < 5; i++) acquire(30);
    assert(thermalBlocked());
    sts.missing[5] = false;
    acquire(45, 5); acquire(45, 5); acquire(45, 5);
    assert(!thermalBlocked());
  } else if (mode == "retry_stop") {
    sts.dropStop = true;
    hot();
    int attempts = sts.stopPackets;
    assert(sts.torque[4]);  // dropped write is not a verified shutdown
    acquire(60); assert(sts.stopPackets == attempts + 1);
    sts.dropStop = false;
    acquire(60);
    assert(sts.stopPackets == attempts + 2 && !sts.torque[4]);
  } else if (mode == "incident") {
    for (int t : {50, 52, 57, 59}) acquire(t);
    assert(thermalBlocked());
    acquire(58);
    command("TA 1"); refused();
    command("W2 4 48 1000"); refused();
    command("W1 4 40 1"); refused();
    binary('W', 1); refused();
    assert(sts.enableWrites == 0 && sts.motionWrites == 0);
  } else { return 2; }
}
"""


@pytest.fixture(scope="module")
def thermal_sketch(tmp_path_factory):
    compiler = shutil.which("clang++") or shutil.which("c++")
    assert compiler, "A C++ compiler is required to validate the thermal interlock"
    source = SKETCH.read_text()
    source = re.sub(r'^#include (?:<Wire.h>|<SCServo.h>|"st7789_tft.h")\n', "", source, flags=re.M)
    # Arduino generates forward declarations; mimic that for the unmodified
    # function bodies, then compile the entire sketch against fake hardware.
    declarations = re.findall(
        r"^((?:static )?(?:void|bool|int|int16_t|uint8_t|uint16_t) \w+\([^;{}]*\))\s*\{",
        source, re.M,
    )
    directory = tmp_path_factory.mktemp("thermal_sketch")
    cpp = directory / "thermal.cpp"
    cpp.write_text(IO + "\n" + ";\n".join(declarations) + ";\n" + source + CASES)
    executable = directory / "thermal"
    build = subprocess.run([compiler, "-std=c++17", "-O0", str(cpp), "-o", str(executable)],
                           capture_output=True, text=True)
    assert build.returncode == 0, build.stderr
    return executable


@pytest.mark.parametrize("case", [
    "boot", "confirmation", "freshness", "bypasses", "multiple", "retry_stop", "incident",
])
def test_thermal_cooldown(thermal_sketch, case):
    subprocess.run([str(thermal_sketch), case], check=True, capture_output=True, text=True)
