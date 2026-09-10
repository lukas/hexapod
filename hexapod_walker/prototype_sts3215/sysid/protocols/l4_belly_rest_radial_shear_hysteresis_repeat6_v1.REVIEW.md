# Review record — `l4_belly_rest_radial_shear_hysteresis_repeat6_v1`

Protocol content hash (canonical JSON, `sysid_protocol.protocol_hash`):
**`a77e379c68c5`**. File sha256
`23b4e54b4d206f6f58e601510888bef0c8b70e27fdba5bac545cfcffbe8211ad`.
Reviewed 2026-09-10 for experiment `7299f24343654f9893274d4328b277ad`
(engineering job `21b9b738950646a294d651a1a1aadd24`).

Sixth and final leg of the belly-rest backlash family. L4 is the one leg with
no number at all: the ladder in `l3_two_run_pooled.json` lists L1, L2, L3, L5
and L0. This completes the six-leg set.

## Trusted deterministic executor

`POST /api/sysid/run` on the robot web server, accepting `sysid_protocol`
schema version 1 (`linux_control/sysid_protocol.py` +
`linux_control/sysid_runner.py`, the streaming executor with in-loop
current/temperature/tracking/missing-feedback trips and a final limp). This is
the same named executor that ran the L5, L2, L1, L0 and L3 members of this
family byte-exact.

Installed-source identity was verified FRESH for this run (not reused), by
md5sum over ssh against the live install at
`/home/arduino/hexapod_sts/linux_control` — the path taken from
`systemctl cat hexapod-web.service` (`WorkingDirectory`), not guessed. All
five executor files compare equal to this checkout:

| file | md5 |
|---|---|
| `sysid_runner.py` | `5983395937e756836bdc32b019a13645` |
| `sysid_protocol.py` | `1380fdcfb967a13221cae5b5b272853b` |
| `command_lease.py` | `4451d79563b880b8a048410474d8139f` |
| `mcu_feetech_bus.py` | `1115a6de9a1038a0db20383f63d9a7cc` |
| `async_bus_guard.py` | `6fb9b393daa5f7290dd38fadd1e0b699` |

**Gotcha worth recording:** the robot also carries a stale
`/home/arduino/linux_control` directory holding an OLD `mcu_feetech_bus.py`
(md5 `5e80d6075f1a9d0315a81fe6fb7666fe`) and none of the other four files.
md5summing *that* path reports a mismatch that looks like deployment drift and
is not — it is simply the wrong directory. **Nothing was deployed for this run.**

This is the current evidence that resolves the saved plan's creation-time
`_adaptive_admission.ready: false` — its two stated reasons were that the
proposal "has not proved current runtime compatibility" and "does not yet name
an available trusted deterministic executor". Both are answered above; the
plan's historical parameters are unchanged.

## How it was produced

```sh
python3 sysid/generate_l5_leg_variant.py \
  sysid/protocols/l5_belly_rest_radial_shear_hysteresis_repeat6_v1.json \
  --leg 4 --strict-independent --created 2026-09-10T16:35:00-07:00
```

The saved plan derives the protocol from `a99ceef28136` (the L2 member), but
the generator only accepts an `l5_`-named source. Rather than assume the two
routes agree, the generator was first proved to reproduce the **committed L3
protocol byte-for-byte** from the L5 source (`--leg 3`, same flags,
`diff` identical), and then the L2-derivation claim was verified directly on
the L4 output. Both hold:

- L2's canonical hash recomputes to `a99ceef28136`, matching the plan exactly.
- `l4[13] == l2[7]` (hip) and `l4[14] == l2[8]` (knee) at **all 1560 ticks**.
- `t_s` identical to L2's; one `traj` segment; 1560 ticks; 10 Hz.
- Every non-trajectory field compares equal to L2: `sysid_protocol` 1,
  `hz` 10, `write_speed` 180, `write_acc` 10, `soft_torque` 700,
  `max_current_a` 0.75, `current_trip_polls` 3, `hard_current_a` 3.0,
  `home_deg` all zero. **No parameter was edited.**
- Moving joints are exactly `{13, 14}`, matching the plan's
  `hip_joint` 13 / `knee_joint` 14. `j12` (L4 yaw) is constant `0` in all
  1560 rows, so the leg does not sweep laterally. The other 16 joints are
  exactly `0.0`. First and last rows are all-zero.
- The remap is **axis-preserving**: `axis_of(j) = AXES[j % 3]`, so L2's
  j7/j8 are (hip, knee) and L4's j13/j14 are (hip, knee) too.
- `sysid_protocol.validate()` returns no errors.

## Foot clearance

Computed with the project's own `linux_control/geometry_plant.py`
(`foot_z_mm`/`foot_r_mm`), which take no leg index and are leg-agnostic; the
knee is the tibia's **absolute** leg-plane angle, as that module's own header
states.

- Deepest commanded `foot_z` **−15.00 mm**; measured first floor contact
  **−80.95 mm** ⇒ **65.95 mm clear**, against a 15 mm requirement.
- Radius from the yaw axis 192.499 → 252.500 mm, a 60.00 mm radial travel:
  a 60 mm long, 15 mm deep sliver directly along the leg L4 already rests on.
- The whole z profile is identical to L2's tick-for-tick.

**Correction to the plan's wording.** The plan says "a relative-knee
reconstruction gives a wrongly deep answer". Measured, the relative
reconstruction is *shallower* at all 1560 ticks (min −0.000 mm vs the absolute
−15.000 mm) and never deeper. The plan's parenthetical is inverted for this
family — but conservatively: the mandated absolute convention yields the
**deeper** reading, so the 15 mm gate is judged against the stricter number
and still passes with 65.95 mm.

## Tests

`linux_control/test_sysid_runner_guards.py`,
`linux_control/test_command_lease.py` and `sysid/tests`: **81 passed**.

The saved plan needed no new per-leg registry entry:
`sysid/qualify_repeat_runner.py`'s `PROTOCOLS` table covers the L2/L5 *air*
fault-injection suite and is not a per-leg registry of belly-rest members.
