"""The host-lost / auto-limp check must survive lastHostMs being newer than
the loop's `now`.

2026-09-22, hexapod2: the bridge cut torque on all 18 servos twice while the
robot stood still, about a minute after a move, with the host talking the
whole time.  loop() sampled `now` first, the stream passes pumped host bytes
and stamped lastHostMs with a later millis(), and the unsigned difference
wrapped to ~4e9 ms: "host lost", torque off.  The fixed sketch re-samples the
clock and compares signed.  This test pins the arithmetic (compiled with the
host C compiler) and the shape of the check in the sketch."""
from pathlib import Path
import shutil
import subprocess

import pytest

INO = Path(__file__).resolve().parents[1] / "feetech_bridge" / "feetech_bridge.ino"


def test_sketch_compares_host_silence_signed_with_fresh_clock():
    src = INO.read_text()
    assert "const long sinceHostMs = (long)(millis() - lastHostMs);" in src
    assert "sinceHostMs > (long)HOST_LIMP_MS" in src
    assert "now - lastHostMs > HOST_LOST_MS" not in src, "unsigned wrap bug is back"
    assert "now - lastHostMs > HOST_LIMP_MS" not in src, "unsigned wrap bug is back"
    assert "dbgAutoLimps++" in src, "auto-limps must stay countable (DBG auto_limps)"


@pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler")
def test_signed_difference_treats_future_stamp_as_just_heard(tmp_path):
    c = tmp_path / "t.c"
    c.write_text(r"""
#include <stdio.h>
#include <stdint.h>
typedef uint32_t ul;
int main(void) {
  ul now = 2149, lastHostMs = 2150;               /* pumped 1 ms after `now` */
  int buggy = (now - lastHostMs) > 30000UL;        /* the old check */
  long since = (long)(int32_t)(now - lastHostMs);   /* the fixed check */
  int fixed = since > 30000L;
  ul late_now = 2150 + 30001;                       /* genuinely silent 30 s */
  int still_trips = (long)(int32_t)(late_now - lastHostMs) > 30000L;
  printf("%d %d %d\n", buggy, fixed, still_trips);
  return 0;
}
""")
    exe = tmp_path / "t"
    subprocess.run(["cc", "-O0", str(c), "-o", str(exe)], check=True)
    out = subprocess.run([str(exe)], check=True, capture_output=True, text=True).stdout.split()
    assert out == ["1", "0", "1"], out   # old check trips on a future stamp, new one does not, real silence still trips
