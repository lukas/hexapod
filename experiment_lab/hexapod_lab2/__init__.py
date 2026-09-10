"""Robot Lab v2: one small loop.

    health read (<= 10 s)  ->  run a protocol  ->  record  ->  plan (<= 2 min)

The robot's own in-loop trips (current, temperature, load, tilt, servo
loss) are the safety system. There is no pre-run checklist and none will be
added here: the health read is a skip-or-go so a dark robot costs one HTTP
call, not a runner launch. Plans that need code are handed to one builder
subagent with a hard wall clock; the loop keeps running other plans
meanwhile. The loop stops itself on three failed runs in a row, a robot
unreachable twice in a row, an empty planner twice in a row, or the daily
spend cap.
"""
