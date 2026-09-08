# Cartesian foot frame correction — copy-only handoff

Prepared from the live cloud source without editing it. Root should compare
current owner progress before copying or applying this patch.

Expected pre-change `rl_move/sim/cart_foot_decode.py` SHA-256:
`d23f273756da34b208b98c4e172f31b3b43995138c5434c0fef72d72ecf3fa86`

Expected post-change helper SHA-256:
`39360918c7e597c18c53d19034edc4554c5d6d0095ccfc1059b5106408b16053`

The zero-pose foot projection includes lateral offsets; it is not the pitch
plane's radial axis. Defining the frame from that projection makes an exact
planar chain look tilted. An in-memory check on the cloud's nominal mesh twin
reduced the 200-pose FK error from 0.002076195675 m to 1.77e-16 m and retained
zero-action stance parity (3.89e-16 rad). No kinematic tolerance needs relaxing.

Exact old snippet:
```python
            ex = x0 / n
            ey = np.cross(ez, ex)
```

Exact replacement:
```python
            # The foot's lateral offset does not define the pitch
            # plane. Use the pitch axis itself, projected perpendicular
            # to yaw, and retain the outward radial sign convention.
            ey = data.xaxis[jp].copy()
            ey -= np.dot(ey, ez) * ez
            pitch_norm = np.linalg.norm(ey)
            if pitch_norm < 1e-9:
                raise ValueError(f"leg {leg}: pitch axis parallel to yaw axis")
            ey /= pitch_norm
            ex = np.cross(ey, ez)
            if np.dot(ex, x0) < 0.0:
                ex, ey = -ex, -ey
```

Only the frame construction changes. Existing joint/site and planar-axis
checks, IK branches, annulus projection, axis limits, default-off wiring,
reward, plant, action dimensionality and reset state remain unchanged. The
new parallel-axis check prevents division by zero before the existing guard.
This nominal decoder continues to ignore hidden per-episode geometry DR.

Files to copy: the corrected helper and new `rl_move/tests/test_cart_foot_frame.py`.
`frame_fix.patch` contains exactly those two changes. The existing owner's
`test_cart_foot_decode.py` is not replaced; its broad-FK 3.5 mm tolerance and
“irreducible CAD tilt” commentary should be tightened by the owner. New tests
cover nominal MuJoCo FK, IK from actual MuJoCo foot positions, zero-action
stance/default-off targets, and rejection of parallel pitch/yaw axes.

Validation: `test_cart_foot_frame.py` — **4 passed in 0.51 s** using the existing
project uv environment. The existing eight-test bank was not rerun. Decoder-only
benchmark on controller: 71.65 microseconds per 18-joint call (~13,956 calls/s/core).
No live-file changes, deployment, launch, or Git metadata mutation were performed
by this handoff.

## Concurrent owner bank change to reconcile

At 04:43 UTC the owner added `test_primitive_family_fail_closed`, attributing
its old rejection to an inherent ~6-degree axis tilt. The corrected frame
also fits that primitive model to numerical precision (200-pose FK max
1.73e-16 m; zero-action error 3.89e-16 rad). Thus this new test encodes the
same old frame bug as a family restriction and will fail after the fix.
Replace that geometric assertion with an actually malformed-axis guard test
(the new frame bank includes one), or separately enforce a deliberate
mesh-only experiment eligibility rule. Do not preserve a coordinate bug to
implement model eligibility. No primitive experiment is proposed here.


## Root integration

Root verified the expected full source SHA before surgically applying the
pitch-plane correction on the controller. It also removed the inaccurate DR
bound comment, tightened the owner's nominal FK tolerance to1e-9m, and
replaced the false primitive-geometry rejection with a deliberately
nonparallel knee-axis rejection. No primitive experiment was introduced.
The additional independent four-test bank was copied unchanged. Combined
owner+frame bank:12passed in1.26s on controller. Current helper SHA256:
bb7010d8383798316316a0e6faf1176d3dd6f838c62d1458c7ee68aa866ef26b.
This differs from the proposed handoff hash only by comments/wording.
Training owner042639 retains its runtime wiring and final snapshot/launch.
No training was started by this repair.
