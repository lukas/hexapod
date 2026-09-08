# Launch pipe repair

The training launcher backgrounded a shell AND-list: `cd WORKDIR && nohup TRAIN ... & echo $!`. Its wrapper retained kubectl stdout/stderr pipes while the trainer ran. This made an already-running trainer look like a timed-out command until the existing PID recovery path handled it.

Read-only evidence on train3 at 2026-09-08 08:16:19 UTC: trainer PID2855025 and uv PID2855020 had stdin=/dev/null and stdout/stderr=the training log. Their still-live bash parent PID2855019 retained fd1 pipe:[177451102] and fd2 pipe:[177451103]. The inspected parent command exactly matched the AND-list construction. kexec's default timeout is60s, not120s; deliberate verification waits remain separate.

The new command runs cd in the foreground and aborts on failure, then backgrounds only the redirected trainer. It preserves uv, environment, logfile/stdin redirects, PID capture, training arguments and the existing verification waits. No live trainer was signalled or restarted.

Real-shell regression reproduces the old timeout with an already-started child, then proves the corrected command closes both captured pipes while its bounded child remains alive. It checks environment, cwd, stdin EOF, logged stderr, failed-directory abort and no fake PID. Only local test process groups are cleaned up. Combined with the existing torch gate tests:17 passed locally in0.95s; controller validation recorded in the heartbeat receipt.

This fixes launch-control latency. It does not increase PPO speed or eliminate compilation/verification time.
