# Angle-path verification — 2026-09-14

The physical H1 absolute-tibia conversion is deployed. The normal STEP rise and lower were repaired and observed completing after the recovery described in HARDWARE_JOINT_FRAME.md. The earlier tucked-leg/clearance statements there describe a historical state, not an outstanding request for hands-on help.

The stand generator now enforces both absolute-link and relative-hinge limits, including replant allowance. Its simulation runner now sends logical commands through ServoProfile.command_robot_abs. Exported standup_modes.json declares the joint contract; every trajectory sample is motor-limit checked before export. Legacy metadata alone is not evidence of coordinate correctness.

A normal descent starts at measured standing support instead of trying to drag loaded feet onto a nominal first keyframe. Complete pose reads retry at most three coherent acquisitions; they never fill a missing hip or knee from a different sample. A glide timeout reports failure, not completion. Direct stance validates before arming and preloads present goals before enabling torque.

Physical results: the final STEP rise completed in 13.81 s (2.44 A peak), followed by a normal STEP lower in 11.13 s (2.36 A peak). The lower reached maximum absolute logical angle 0.35 deg; both camera views and three healthy complete feedback samples established grounding before torque-off. There was no observed fall or collision. Camera 0 covered the full robot; an outer leg reached camera 1's edge during repositioning. All 18 servos answered and current was zero after disarm. L0 knee warmed to 56 C; the robot was left off. Standing retained about 8 deg of loaded tracking error. These results establish functional transitions, not precise optical calibration or reliable RL steering.

Evidence: project workspace artifacts/h1-angle-paths-20260914/ (raw replies, snapshots, recordings, test/deploy logs and README). The two-camera excerpts have irregular source frame timing and are not synchronized metrology.

Deployed hardware source: 34c2ac545, codex/h1-complete-angle-paths-20260914. The cleanup integration restores the complete physical angle patch and present-position arming without restoring the retired P/ASCII transport. Pose compatibility methods read S snapshots. Do not deploy an older cleanup-only branch missing this integration.

Final integration validation: make test-fast passed (3865 passed, 23 skipped, 1 expected failure, 68.22 s). The last passive H1 check found 18/18 motors, zero current, motors off and the hottest knee cooled to 50 C.
