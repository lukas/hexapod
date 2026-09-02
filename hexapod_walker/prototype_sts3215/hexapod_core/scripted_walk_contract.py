"""Shared timing and servo-profile contract for scripted walking.

These constants are consumed by both the physical DriveController and the
MuJoCo web/replay session.  Keeping them here prevents the two paths from
quietly acquiring different target cadences or STS motion profiles again.
"""

SCRIPTED_WALK_CONTROL_HZ = 100.0
SCRIPTED_WALK_DT_S = 1.0 / SCRIPTED_WALK_CONTROL_HZ

# STS3215 WritePosEx units.  The previous physical scripted profile was
# 1500/30; this raised experiment contract is deliberately scoped to walking
# and does not change the gentler stand, sit, or hold profiles.
SCRIPTED_WALK_SPEED_COUNTS_S = 2000
SCRIPTED_WALK_ACC_UNITS = 80

