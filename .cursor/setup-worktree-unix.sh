#!/bin/sh
# Cursor runs this in every NEW worktree it creates (wired up via
# .cursor/worktrees.json). Also safe to run by hand in a worktree made with
# plain `git worktree add`. It gives the worktree a working Python env and
# the machine-local files git does not carry.
#
#   ROOT_WORKTREE_PATH=/Users/lukas/hexapod sh .cursor/setup-worktree-unix.sh
set -eu
ROOT="${ROOT_WORKTREE_PATH:?ROOT_WORKTREE_PATH not set (pass the main checkout path, e.g. /Users/lukas/hexapod)}"

# The vision system is a git submodule; `git worktree add` does not
# initialise submodules, and `uv sync` fails on the missing path otherwise.
git submodule update --init --depth 1 hexapod_walker/prototype_sts3215/hexapod-tracker

# Per-worktree venv from the shared uv.lock. uv hard-links wheels from its
# cache, so after the first machine-wide download this takes seconds and a
# few MB. A per-worktree env is REQUIRED (not just allowed): the editable
# install points at THIS checkout's source tree, so agents in different
# worktrees import their own code instead of the main checkout's.
uv sync --frozen

# Share the pulled RL checkpoints (gigabytes, pulled from CoreWeave, not in
# git). A symlink keeps one cache for all worktrees.
POL=hexapod_walker/prototype_sts3215/rl_move/sim/policies
if [ -d "$ROOT/$POL" ] && [ ! -e "$POL" ]; then
  ln -s "$ROOT/$POL" "$POL"
fi

# MCP config is gitignored; copy it so worktree agents get the same servers.
if [ -f "$ROOT/.mcp.json" ] && [ ! -e .mcp.json ]; then
  cp "$ROOT/.mcp.json" .mcp.json
fi
