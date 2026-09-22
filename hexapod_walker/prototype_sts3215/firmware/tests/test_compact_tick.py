"""Cross-check the compact 'T'/'t' tick between firmware and host (2026-09-22).

Compiles the sketch's ``sendSnapshotCompact`` and ``binPayloadNeed`` with fake
IO, captures the exact bytes the MCU would put on the wire, and decodes them
with the host parser (``mcu_feetech_bus.parse_tick_payload``).  A layout drift
on either side fails here before it reaches a robot.
"""

from pathlib import Path
import shutil
import struct
import subprocess
import sys

import pytest

HERE = Path(__file__).resolve()
FIRMWARE = HERE.parents[1] / "feetech_bridge" / "feetech_bridge.ino"
sys.path.insert(0, str(HERE.parents[2] / "linux_control"))
sys.path.insert(0, str(HERE.parents[2] / "linux_control" / "vendor"))


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
                return source[start: offset + 1]
    raise AssertionError(f"unterminated function: {signature}")


@pytest.fixture(scope="module")
def harness(tmp_path_factory):
    compiler = shutil.which("clang++") or shutil.which("c++")
    if compiler is None:
        pytest.skip("A C++ compiler is required for the firmware regression")
    source = FIRMWARE.read_text()
    functions = [
        _extract_function(source, "static int16_t binPayloadNeed(uint8_t cmd, uint8_t n) {"),
        _extract_function(source, "static void fillDefaultIds(uint8_t *ids, uint8_t &n) {"),
        _extract_function(source, "static void sendBinHeader(uint8_t cmd, uint8_t n, uint8_t &x) {"),
        _extract_function(source, "static void sendBinByte(uint8_t b, uint8_t &x) {"),
        _extract_function(source, "static void sendSnapshotCompact() {"),
    ]
    stubs = r"""
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <string>
typedef int16_t s16; typedef uint16_t u16; typedef uint8_t u8;
static const uint8_t ID_LO = 2, ID_HI = 19, MAX_N = 18;
struct FakeSerial { void write(uint8_t b) { printf("%02x", b); } } Serial1;
static uint32_t dbgBinReplyHeaders = 0;
static unsigned long posStampMs = 1000, imuStampMs = 1000;
static bool imuCacheValid = true;
static uint16_t posSeq = 0x1234;
static int16_t posCache[MAX_N], spdCache[MAX_N], imuCache[7];
static uint8_t posOk[MAX_N];
static uint16_t ageMs(unsigned long stamp, bool valid) { return valid ? (uint16_t)(stamp == 1000 ? 3 : 0) : 0xFFFF; }
"""
    main = r"""
int main(int argc, char **argv) {
  std::string mode = argv[1];
  if (mode == "need") {
    printf("%d %d %d %d %d %d %d %d %d", binPayloadNeed('S', 18), binPayloadNeed('S', 0),
           binPayloadNeed('W', 19), binPayloadNeed('F', 0), binPayloadNeed('P', 18),
           binPayloadNeed('T', 18), binPayloadNeed('T', 0), binPayloadNeed('V', 1),
           binPayloadNeed('X', 1));
    return 0;
  }
  for (int k = 0; k < MAX_N; k++) { posCache[k] = 2000 + k; spdCache[k] = -30 + k; posOk[k] = (k == 5) ? 0 : 1; }
  int16_t imu[7] = {100, -200, 16384, -5, 6, -7, 1234};
  for (int i = 0; i < 7; i++) imuCache[i] = imu[i];
  if (mode == "noimu") imuCacheValid = false;
  sendSnapshotCompact();
  return 0;
}
"""
    directory = tmp_path_factory.mktemp("firmware_compact_tick")
    cpp = directory / "compact_tick.cpp"
    exe = directory / "compact_tick"
    cpp.write_text("\n".join((stubs, *functions, main)))
    subprocess.run([compiler, "-std=c++17", "-O0", str(cpp), "-o", str(exe)],
                   check=True, capture_output=True, text=True)
    return exe


def test_payload_size_table(harness):
    out = subprocess.check_output([str(harness), "need"], text=True).split()
    assert list(map(int, out)) == [108, 0, 0, 0, 18, 36, 0, 3, -1]


def test_firmware_compact_reply_decodes_with_the_host_parser(harness):
    from mcu_feetech_bus import (parse_tick_payload, parse_snapshot_payload,
                                 TICK_HEAD_LEN, TICK_REC_LEN, SNAP_HEAD_LEN,
                                 SNAP_REC_LEN)
    raw = bytes.fromhex(subprocess.check_output([str(harness), "wire"], text=True))
    assert raw[:4] == bytes([0xA5, 0x5A, ord("t"), 18])
    body = raw[2:-1]
    x = 0
    for b in body:
        x ^= b
    assert raw[-1] == x, "checksum covers cmd, n and payload"
    payload = raw[4:-1]
    assert len(payload) == TICK_HEAD_LEN + 18 * TICK_REC_LEN
    assert len(raw) == 100          # the 's' reply is 134 bytes
    snap = parse_tick_payload(18, payload)
    assert snap["seq"] == 0x1234 and snap["pos_age_ms"] == 3 and snap["imu_age_ms"] == 3
    assert snap["imu_raw"] == (100, -200, 16384, -5, 6, -7, 1234)
    assert [s["id"] for s in snap["servos"]] == list(range(2, 20))
    assert [s["ok"] for s in snap["servos"]] == [k != 5 for k in range(18)]
    assert snap["servos"][17]["pos_counts"] == 2017
    assert snap["servos"][0]["spd_counts_s"] == -30
    # Byte-for-byte the same information the 's' path would have carried.
    s_payload = struct.pack("<HHH", 0x1234, 3, 3) + struct.pack("<7h", *snap["imu_raw"])
    for k in range(18):
        s_payload += struct.pack("<BBhh", 2 + k, int(k != 5), 2000 + k, -30 + k)
    assert len(s_payload) == SNAP_HEAD_LEN + 18 * SNAP_REC_LEN
    assert parse_snapshot_payload(18, s_payload) == snap


def test_firmware_compact_reply_invalid_imu_age(harness):
    from mcu_feetech_bus import parse_tick_payload, SNAP_AGE_INVALID
    raw = bytes.fromhex(subprocess.check_output([str(harness), "noimu"], text=True))
    snap = parse_tick_payload(18, raw[4:-1])
    assert snap["imu_age_ms"] == SNAP_AGE_INVALID
