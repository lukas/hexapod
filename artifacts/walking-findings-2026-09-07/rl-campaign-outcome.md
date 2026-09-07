# RL walking campaign outcome

Both candidate arms were rejected in simulation; neither produced an improved controller export for a new robot trial. The existing Candidate B remains the physical baseline.

- Stride: removing the imitation anchor collapsed leg cycling (0/24 valid gaits), with little useful travel and4/24 simulated safety terminations. This does not establish a hardware timing ceiling.
- Turns: the recovered continuation completed and retained24/24 valid gaits with zero falls or sacrificed legs. Pure-turn errors improved from0.108/0.100 to0.078/0.085, but changing-command course error worsened from8.55° to10.2° and combined-arc tracking barely changed. Reward rose throughout. The final owner classified this as reward/objective misalignment and produced no export.

The next training change should make the yaw/course reward match the desired joystick course response before spending more steps on the same recipe. This campaign is complete; the general RobotLab watchdog continues. No new physical experiment or offline review was queued.

Evidence: turns-resume1-final-verdict-mcp.json (owner cycle20260906T063539 finished2026-09-06 at07:04:17UTC), stride-final-get-run.json, campaign.json and handoffs.json. The earlier interrupted continuation remains recorded separately; rejection is based on the completed evaluation, not that interruption or an inferred user budget cap.
