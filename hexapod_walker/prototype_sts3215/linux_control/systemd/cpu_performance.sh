#!/bin/sh
# Called as root by hexapod-web.service before the unprivileged web process.
# Optional cpufreq root is for offline fixture checks; the service passes none.
# This dedicated controller needs its CPU budget even while UART I/O sleeps.

cpu_root=${1:-/sys/devices/system/cpu/cpufreq}
found=0
warn() { printf 'hexapod-cpu: WARNING: %s\n' "$*" >&2; }

for policy in "$cpu_root"/policy*; do
    [ -d "$policy" ] || continue
    found=1
    available=$(cat "$policy/scaling_available_governors" 2>/dev/null) || available=
    case " $available " in
        *" performance "*) ;;
        *) warn "$policy: performance governor unavailable; leaving CPU policy unchanged"; continue ;;
    esac
    previous=$(cat "$policy/scaling_governor" 2>/dev/null) || previous=unknown
    if [ "$previous" != performance ]; then
        if ! printf '%s\n' performance > "$policy/scaling_governor"; then
            warn "$policy: could not set performance governor; check sysfs permissions"
            continue
        fi
    fi
    actual=$(cat "$policy/scaling_governor" 2>/dev/null) || actual=unknown
    if [ "$actual" = performance ]; then
        printf 'hexapod-cpu: %s governor=%s (previous=%s)\n' "$policy" "$actual" "$previous"
    else
        warn "$policy: requested performance but read back $actual"
    fi
done

[ "$found" -eq 1 ] || warn "no cpufreq policy directories under $cpu_root; CPU policy unchanged"
# CPU tuning must never prevent the control service from starting.
exit 0
